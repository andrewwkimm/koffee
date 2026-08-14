"""Persistent state for interrupted Koffee jobs."""

import hashlib
import json
import os
import shutil
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from platformdirs import user_state_path
from pydantic import BaseModel, ConfigDict

from koffee.schemas.config import KoffeeConfig
from koffee.schemas.domain import (
    Segment,
    Transcript,
)

_SAMPLE_BYTES = 1_048_576
_JOB_ID_LENGTH = 24


class InputFingerprint(BaseModel):
    """Stable identity for one input file."""

    model_config = ConfigDict(frozen=True)

    path: str
    size: int
    modified_nanoseconds: int
    sample_digest: str


class TranscriptionSettings(BaseModel):
    """Settings that determine an ASR result."""

    model_config = ConfigDict(frozen=True)

    transcription_model: str
    compute_type: str
    device: str
    source_language: str
    vad_filter: bool


class TranslationSettings(BaseModel):
    """Settings that determine translated chunk content."""

    model_config = ConfigDict(frozen=True)

    source_language: str
    target_language: str
    instructions_digest: str
    chunk_size: int
    context_size: int


class SavedChunk(BaseModel):
    """One validated translated chunk."""

    model_config = ConfigDict(frozen=True)

    start_entry: int
    source_segments: tuple[Segment, ...]
    translated_segments: tuple[Segment, ...]
    translator: str
    translation_model: str


def translation_instructions_digest(
    instructions: str,
) -> str:
    """Returns a stable translation-instructions digest."""
    return hashlib.sha256(instructions.encode()).hexdigest()


class JobManifest(BaseModel):
    """Metadata required to validate a checkpoint."""

    model_config = ConfigDict(frozen=True)

    fingerprint: InputFingerprint
    transcription: TranscriptionSettings
    saved_config: dict[str, Any]


class JobStore:
    """Owns checkpoint files for one input."""

    def __init__(
        self,
        directory: Path,
        manifest: JobManifest,
    ) -> None:
        """Initializes storage for one checkpointed job."""
        self.directory = directory
        self.manifest = manifest

    @classmethod
    def open(
        cls,
        input_path: Path | str,
        config: KoffeeConfig,
    ) -> "JobStore":
        """Opens or creates the checkpoint for one input."""
        fingerprint = fingerprint_input(input_path)
        directory = _job_root() / _job_id(fingerprint.path)
        manifest_path = directory / "manifest.json"
        expected_settings = _transcription_settings(config)

        if manifest_path.is_file():
            manifest = JobManifest.model_validate_json(manifest_path.read_text())
            if manifest.fingerprint != fingerprint:
                raise ValueError(
                    "The input file changed after its checkpoint was created."
                )
            if manifest.transcription != expected_settings:
                raise ValueError(
                    "The transcription settings do not match the existing checkpoint."
                )
            return cls(directory, manifest)

        manifest = JobManifest(
            fingerprint=fingerprint,
            transcription=expected_settings,
            saved_config=config.model_dump(
                mode="json",
                exclude={"api_key"},
            ),
        )
        directory.mkdir(
            parents=True,
            exist_ok=True,
        )
        _write_json_atomic(
            manifest_path,
            manifest.model_dump(mode="json"),
        )
        return cls(directory, manifest)

    @classmethod
    def open_existing(
        cls,
        input_path: Path | str,
    ) -> "JobStore":
        """Opens an existing checkpoint without new settings."""
        fingerprint = fingerprint_input(input_path)
        directory = _job_root() / _job_id(fingerprint.path)
        manifest_path = directory / "manifest.json"

        if not manifest_path.is_file():
            raise FileNotFoundError(f"No checkpoint exists for {fingerprint.path}.")

        manifest = JobManifest.model_validate_json(manifest_path.read_text())
        if manifest.fingerprint != fingerprint:
            raise ValueError("The input file changed after its checkpoint was created.")
        return cls(directory, manifest)

    def load_transcript(
        self,
    ) -> Transcript | None:
        """Loads the validated ASR result when available."""
        path = self.directory / "transcript.json"
        if not path.is_file():
            return None
        return Transcript.model_validate_json(path.read_text())

    def save_transcript(
        self,
        transcript: Transcript,
    ) -> None:
        """Atomically saves a validated ASR result."""
        _write_json_atomic(
            self.directory / "transcript.json",
            transcript.model_dump(mode="json"),
        )

    def prepare_translation(
        self,
        settings: TranslationSettings,
        translator: str,
        translation_model: str,
        allow_mixed_translation: bool,
    ) -> None:
        """Validates settings and provenance before resuming."""
        settings_path = self.directory / "translation.json"
        if settings_path.is_file():
            saved = TranslationSettings.model_validate_json(settings_path.read_text())
            if saved != settings:
                raise ValueError(
                    "The translation settings do not match the existing checkpoint."
                )
        else:
            _write_json_atomic(
                settings_path,
                settings.model_dump(mode="json"),
            )

        chunks = self.load_chunks()
        if not chunks:
            return

        previous = chunks[-1]
        changed = (
            previous.translator != translator
            or previous.translation_model != translation_model
        )
        if changed and not allow_mixed_translation:
            raise ValueError(
                "This checkpoint contains chunks "
                "translated by "
                f"{previous.translator}/"
                f"{previous.translation_model}. "
                "Use --allow-mixed-translation to "
                "continue with another translator "
                "or model."
            )

    def load_chunks(
        self,
    ) -> list[SavedChunk]:
        """Loads the contiguous translated-chunk prefix."""
        directory = self.directory / "chunks"
        if not directory.is_dir():
            return []

        chunks = [
            SavedChunk.model_validate_json(path.read_text())
            for path in sorted(directory.glob("*.json"))
        ]

        expected_entry = 1
        for chunk in chunks:
            if chunk.start_entry != expected_entry:
                raise ValueError("Translation checkpoint chunks are not contiguous.")
            expected_entry += len(chunk.source_segments)

        return chunks

    def save_chunk(
        self,
        chunk: SavedChunk,
    ) -> None:
        """Atomically saves one validated translated chunk."""
        if len(chunk.source_segments) != len(chunk.translated_segments):
            raise ValueError("Cannot save an incomplete translated chunk.")

        destination = self.directory / "chunks" / f"{chunk.start_entry:08d}.json"
        _write_json_atomic(
            destination,
            chunk.model_dump(mode="json"),
        )

    def delete(self) -> None:
        """Deletes a completed job checkpoint."""
        shutil.rmtree(
            self.directory,
            ignore_errors=True,
        )


def list_jobs() -> list[JobStore]:
    """Returns every readable unfinished job."""
    root = _job_root()
    if not root.is_dir():
        return []

    jobs = []
    for manifest_path in sorted(root.glob("*/manifest.json")):
        try:
            manifest = JobManifest.model_validate_json(manifest_path.read_text())
        except (OSError, ValueError):
            continue
        jobs.append(
            JobStore(
                manifest_path.parent,
                manifest,
            )
        )
    return jobs


def fingerprint_input(
    input_path: Path | str,
) -> InputFingerprint:
    """Fingerprints a resolved path and sampled contents."""
    path = Path(input_path).expanduser().resolve(strict=True)
    stat = path.stat()
    digest = hashlib.sha256()

    with path.open("rb") as input_file:
        offsets = {
            0,
            max(
                0,
                stat.st_size // 2 - _SAMPLE_BYTES // 2,
            ),
            max(0, stat.st_size - _SAMPLE_BYTES),
        }
        for offset in sorted(offsets):
            input_file.seek(offset)
            sample = input_file.read(_SAMPLE_BYTES)
            digest.update(offset.to_bytes(8, "big"))
            digest.update(sample)

    return InputFingerprint(
        path=str(path),
        size=stat.st_size,
        modified_nanoseconds=stat.st_mtime_ns,
        sample_digest=digest.hexdigest(),
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


def _transcription_settings(
    config: KoffeeConfig,
) -> TranscriptionSettings:
    """Returns settings that determine ASR output."""
    return TranscriptionSettings(
        transcription_model=config.transcription_model,
        compute_type=config.compute_type,
        device=config.device,
        source_language=config.source_language,
        vad_filter=config.vad_filter,
    )


def _write_json_atomic(
    destination: Path,
    value: object,
) -> None:
    """Writes JSON atomically on the destination filesystem."""
    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
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
            json.dump(
                value,
                temporary_file,
                ensure_ascii=False,
                sort_keys=True,
            )
            temporary_file.flush()
            os.fsync(temporary_file.fileno())

        temporary_path.replace(destination)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
