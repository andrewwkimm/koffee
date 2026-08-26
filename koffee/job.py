"""Persistent state for interrupted Koffee jobs."""

import errno
import hashlib
import json
import logging
import os
import shutil
from pathlib import Path
from tempfile import NamedTemporaryFile
from types import TracebackType
from typing import Any, BinaryIO, Self, TypeVar

from platformdirs import user_state_path
from pydantic import BaseModel, ConfigDict, Field, model_validator

from koffee.exceptions import (
    CheckpointChunkError,
    CheckpointCorruptError,
    CheckpointLockedError,
    CheckpointNotFoundError,
    CheckpointSettingsError,
    CheckpointSourceError,
)
from koffee.schemas.config import KoffeeConfig
from koffee.schemas.domain import Segment, Transcript

log = logging.getLogger(__name__)

_SAMPLE_BYTES = 1_048_576
_JOB_ID_LENGTH = 24
_CHUNK_NAME_WIDTH = 8
_FIRST_ENTRY = 1

_ModelT = TypeVar("_ModelT", bound=BaseModel)


class InputFingerprint(BaseModel):
    """Stable identity for one input file."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    path: str
    size: int
    modified_nanoseconds: int
    sample_digest: str


class TranscriptionSettings(BaseModel):
    """Settings that determine an ASR result."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    transcription_model: str
    compute_type: str
    device: str
    source_language: str
    vad_filter: bool


class TranslationSettings(BaseModel):
    """Settings that determine translated chunk content."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    source_language: str
    target_language: str
    instructions_digest: str
    chunk_size: int
    context_size: int


class SavedChunk(BaseModel):
    """One validated translated chunk."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    start_entry: int = Field(ge=_FIRST_ENTRY)
    source_segments: tuple[Segment, ...]
    translated_segments: tuple[Segment, ...]
    translator: str
    translation_model: str

    @model_validator(mode="after")
    def validate_segments(self) -> Self:
        """Returns a chunk whose source and translation preserve cue structure."""
        if not self.source_segments:
            raise ValueError("A saved chunk must contain at least one segment.")
        if len(self.source_segments) != len(self.translated_segments):
            raise ValueError("Saved source and translated segment counts must match.")
        for source, translated in zip(
            self.source_segments, self.translated_segments, strict=True
        ):
            if (source.start, source.end) != (translated.start, translated.end):
                raise ValueError("Saved translated timestamps must match the source.")
        return self


class JobManifest(BaseModel):
    """Metadata required to validate a checkpoint."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    fingerprint: InputFingerprint
    transcription: TranscriptionSettings
    saved_config: dict[str, Any]


class _JobLock:
    """Owns one nonblocking operating-system file lock."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._file: BinaryIO | None = None

    def acquire(self) -> None:
        """Acquires the lock or raises when another process owns it."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        lock_file = self.path.open("a+b")
        try:
            _lock_file_nonblocking(lock_file)
        except OSError as error:
            lock_file.close()
            if error.errno not in (errno.EACCES, errno.EAGAIN):
                raise
            raise CheckpointLockedError(
                f"Checkpoint is already open: {self.path.stem}."
            ) from error
        self._file = lock_file

    def close(self) -> None:
        """Releases the lock when it is held."""
        if self._file is None:
            return
        self._file.close()
        self._file = None


class JobStore:
    """Owns checkpoint files and the single-writer lock for one input."""

    def __init__(self, directory: Path, manifest: JobManifest, lock: _JobLock) -> None:
        """Initializes storage with an acquired lifetime lock."""
        self.directory = directory
        self.manifest = manifest
        self._lock = lock
        self._closed = False

    @classmethod
    def open(cls, input_path: Path | str, config: KoffeeConfig) -> "JobStore":
        """Opens or creates the exclusively locked checkpoint for one input."""
        fingerprint = fingerprint_input(input_path)
        directory = _job_root() / _job_id(fingerprint.path)
        lock = _acquire_job_lock(directory.name)
        transferred = False
        try:
            manifest = _open_or_create_manifest(directory, fingerprint, config)
            store = cls(directory, manifest, lock)
            transferred = True
            return store
        finally:
            if not transferred:
                lock.close()

    @classmethod
    def open_existing(cls, input_path: Path | str) -> "JobStore":
        """Opens an existing exclusively locked checkpoint without new settings."""
        fingerprint = fingerprint_input(input_path)
        directory = _job_root() / _job_id(fingerprint.path)
        lock = _acquire_job_lock(directory.name)
        transferred = False
        try:
            manifest_path = directory / "manifest.json"
            if not manifest_path.is_file():
                raise CheckpointNotFoundError(
                    f"No checkpoint exists for {fingerprint.path}."
                )
            manifest = _load_model(manifest_path, JobManifest, "manifest")
            if manifest.fingerprint != fingerprint:
                raise CheckpointSourceError(
                    "The input file changed after its checkpoint was created."
                )
            store = cls(directory, manifest, lock)
            transferred = True
            return store
        finally:
            if not transferred:
                lock.close()

    def __enter__(self) -> Self:
        """Returns this open checkpoint store."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Releases the checkpoint lock on context exit."""
        self.close()

    def close(self) -> None:
        """Releases resources owned by this store."""
        if self._closed:
            return
        self._lock.close()
        self._closed = True

    def load_transcript(self) -> Transcript | None:
        """Loads the validated ASR result when available."""
        path = self.directory / "transcript.json"
        if not path.is_file():
            return None
        return _load_model(path, Transcript, "transcript")

    def save_transcript(self, transcript: Transcript) -> None:
        """Atomically saves a validated ASR result."""
        _write_json_atomic(
            self.directory / "transcript.json", transcript.model_dump(mode="json")
        )

    def prepare_translation(
        self,
        settings: TranslationSettings,
        translator: str,
        translation_model: str,
        *,
        allow_mixed_translation: bool,
    ) -> None:
        """Validates settings and every saved chunk's provenance before resuming."""
        settings_path = self.directory / "translation.json"
        if settings_path.is_file():
            saved = _load_model(
                settings_path, TranslationSettings, "translation settings"
            )
            if saved != settings:
                raise CheckpointSettingsError(
                    "The translation settings do not match the existing checkpoint."
                )
        else:
            _write_json_atomic(settings_path, settings.model_dump(mode="json"))

        if allow_mixed_translation:
            self.load_chunks()
            return
        for chunk in self.load_chunks():
            if (
                chunk.translator != translator
                or chunk.translation_model != translation_model
            ):
                raise CheckpointSettingsError(
                    "This checkpoint contains chunks translated by "
                    f"{chunk.translator}/{chunk.translation_model}. Use "
                    "--allow-mixed-translation to continue with another translator "
                    "or model."
                )

    def load_chunks(self) -> list[SavedChunk]:
        """Loads and validates the canonical contiguous translated-chunk prefix."""
        directory = self.directory / "chunks"
        if not directory.is_dir():
            return []
        paths = sorted(directory.iterdir())
        chunks: list[SavedChunk] = []
        expected_entry = _FIRST_ENTRY
        for path in paths:
            expected_name = f"{expected_entry:0{_CHUNK_NAME_WIDTH}d}.json"
            if not path.is_file() or path.name != expected_name:
                raise CheckpointChunkError(
                    f"Unexpected checkpoint chunk file {path.name!r}; expected "
                    f"{expected_name!r}."
                )
            chunk = _load_chunk(path)
            if chunk.start_entry != expected_entry:
                raise CheckpointChunkError(
                    "Translation checkpoint chunks are not contiguous."
                )
            chunks.append(chunk)
            expected_entry += len(chunk.source_segments)
        return chunks

    def save_chunk(self, chunk: SavedChunk) -> None:
        """Saves only the next sequential chunk and permits identical replay."""
        chunks = self.load_chunks()
        expected_entry = (
            _FIRST_ENTRY
            if not chunks
            else chunks[-1].start_entry + len(chunks[-1].source_segments)
        )
        destination = (
            self.directory
            / "chunks"
            / (f"{chunk.start_entry:0{_CHUNK_NAME_WIDTH}d}.json")
        )
        if chunk.start_entry < expected_entry:
            existing = next(
                (saved for saved in chunks if saved.start_entry == chunk.start_entry),
                None,
            )
            if existing == chunk:
                return
            raise CheckpointChunkError(
                f"Checkpoint chunk {chunk.start_entry} conflicts with saved data."
            )
        if chunk.start_entry != expected_entry:
            raise CheckpointChunkError(
                f"Checkpoint chunk starts at {chunk.start_entry}; "
                f": expected {expected_entry}."
            )
        _write_json_atomic(destination, chunk.model_dump(mode="json"))

    def delete(self) -> None:
        """Deletes a completed job checkpoint while retaining its external lock."""
        shutil.rmtree(self.directory, ignore_errors=True)


def translation_instructions_digest(instructions: str) -> str:
    """Returns a stable translation-instructions digest."""
    return hashlib.sha256(instructions.encode()).hexdigest()


def list_jobs() -> list[JobStore]:
    """Returns every readable and currently unlockable unfinished job."""
    root = _job_root()
    if not root.is_dir():
        return []
    jobs = []
    for manifest_path in sorted(root.glob("*/manifest.json")):
        try:
            manifest = _load_model(manifest_path, JobManifest, "manifest")
            lock = _acquire_job_lock(manifest_path.parent.name)
        except (CheckpointCorruptError, CheckpointLockedError, OSError):
            continue
        jobs.append(JobStore(manifest_path.parent, manifest, lock))
    return jobs


def fingerprint_input(input_path: Path | str) -> InputFingerprint:
    """Fingerprints a resolved path and sampled contents."""
    path = Path(input_path).expanduser().resolve(strict=True)
    stat = path.stat()
    digest = hashlib.sha256()
    with path.open("rb") as input_file:
        offsets = {
            0,
            max(0, stat.st_size // 2 - _SAMPLE_BYTES // 2),
            max(0, stat.st_size - _SAMPLE_BYTES),
        }
        for offset in sorted(offsets):
            input_file.seek(offset)
            digest.update(offset.to_bytes(8, "big"))
            digest.update(input_file.read(_SAMPLE_BYTES))
    return InputFingerprint(
        path=str(path),
        size=stat.st_size,
        modified_nanoseconds=stat.st_mtime_ns,
        sample_digest=digest.hexdigest(),
    )


def _open_or_create_manifest(
    directory: Path, fingerprint: InputFingerprint, config: KoffeeConfig
) -> JobManifest:
    """Returns a compatible manifest, replacing stale source state."""
    manifest_path = directory / "manifest.json"
    expected_settings = _transcription_settings(config)
    if manifest_path.is_file():
        manifest = _load_model(manifest_path, JobManifest, "manifest")
        if manifest.fingerprint != fingerprint:
            log.warning(
                "The input file changed after its checkpoint was created; "
                "discarding the stale checkpoint and starting over."
            )
            shutil.rmtree(directory, ignore_errors=True)
        elif manifest.transcription != expected_settings:
            raise CheckpointSettingsError(
                "The transcription settings do not match the existing checkpoint."
            )
        else:
            return manifest
    manifest = JobManifest(
        fingerprint=fingerprint,
        transcription=expected_settings,
        saved_config=config.model_dump(mode="json", exclude={"api_key"}),
    )
    directory.mkdir(parents=True, exist_ok=True)
    _write_json_atomic(manifest_path, manifest.model_dump(mode="json"))
    return manifest


def _load_model(path: Path, model_type: type[_ModelT], description: str) -> _ModelT:
    """Returns validated checkpoint JSON with storage errors translated."""
    try:
        text = path.read_text(encoding="utf-8")
        return model_type.model_validate_json(text)
    except OSError as error:
        raise CheckpointCorruptError(
            f"Cannot read checkpoint {description} at {path.name}."
        ) from error
    except ValueError as error:
        raise CheckpointCorruptError(
            f"Checkpoint {description} at {path.name} is corrupt."
        ) from error


def _load_chunk(path: Path) -> SavedChunk:
    """Returns a validated chunk with chunk-specific corruption context."""
    try:
        return SavedChunk.model_validate_json(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise CheckpointChunkError(
            f"Cannot read checkpoint chunk {path.name}."
        ) from error
    except ValueError as error:
        raise CheckpointChunkError(
            f"Checkpoint chunk {path.name} is corrupt."
        ) from error


def _acquire_job_lock(job_id: str) -> _JobLock:
    """Returns an acquired lock stored outside the deletable job directory."""
    lock = _JobLock(_job_root().parent / "locks" / f"{job_id}.lock")
    lock.acquire()
    return lock


def _lock_file_nonblocking(lock_file: BinaryIO) -> None:
    """Acquires a platform-native exclusive nonblocking file lock."""
    if os.name == "nt":
        import msvcrt  # noqa: PLC0415 -- Windows-only standard library.

        lock_file.seek(0)
        if lock_file.read(1) == b"":
            lock_file.write(b"0")
            lock_file.flush()
            lock_file.seek(0)
        msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
    else:
        import fcntl  # noqa: PLC0415 -- POSIX-only standard library.

        fcntl.flock(
            lock_file.fileno(),
            fcntl.LOCK_EX | fcntl.LOCK_NB,
        )


def _job_root() -> Path:
    """Returns the platform-native Koffee state path."""
    override = os.environ.get("KOFFEE_STATE_DIR")
    if override:
        return Path(override).expanduser() / "jobs"
    return user_state_path("koffee") / "jobs"


def _job_id(resolved_path: str) -> str:
    """Returns the stable identifier for an input path."""
    digest = hashlib.sha256(os.path.normcase(resolved_path).encode()).hexdigest()
    return digest[:_JOB_ID_LENGTH]


def _transcription_settings(config: KoffeeConfig) -> TranscriptionSettings:
    """Returns settings that determine ASR output."""
    return TranscriptionSettings(
        transcription_model=config.transcription_model,
        compute_type=config.compute_type,
        device=config.device,
        source_language=config.source_language,
        vad_filter=config.vad_filter,
    )


def _write_json_atomic(destination: Path, value: object) -> None:
    """Writes JSON atomically on the destination filesystem."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None
    try:
        with NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            prefix=f".{destination.name}.",
            dir=destination.parent,
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            json.dump(value, temporary_file, ensure_ascii=False, sort_keys=True)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        temporary_path.replace(destination)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
