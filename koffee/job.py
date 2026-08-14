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
from koffee.schemas.domain import Transcript

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
                error_message = (
                    "The input file changed after its checkpoint was created."
                )
                raise ValueError(error_message)
            if manifest.transcription != expected_settings:
                error_message = (
                    "The transcription settings do not match the existing checkpoint."
                )
                raise ValueError(error_message)
            return cls(directory, manifest)

        manifest = JobManifest(
            fingerprint=fingerprint,
            transcription=expected_settings,
            saved_config=config.model_dump(
                mode="json",
                exclude={"api_key"},
            ),
        )
        directory.mkdir(parents=True, exist_ok=True)
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
            error_message = f"No checkpoint exists for {fingerprint.path}."
            raise FileNotFoundError(error_message)

        manifest = JobManifest.model_validate_json(manifest_path.read_text())
        if manifest.fingerprint != fingerprint:
            error_message = "The input file changed after its checkpoint was created."
            raise ValueError(error_message)
        return cls(directory, manifest)

    def load_transcript(self) -> Transcript | None:
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
