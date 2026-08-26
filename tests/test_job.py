"""Tests for persistent Koffee jobs."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from koffee.exceptions import (
    CheckpointChunkError,
    CheckpointCorruptError,
    CheckpointLockedError,
    CheckpointSettingsError,
)
from koffee.job import (
    JobStore,
    SavedChunk,
    TranslationSettings,
    fingerprint_input,
)
from koffee.schemas.config import KoffeeConfig
from koffee.schemas.domain import Segment, Transcript


def _transcript() -> Transcript:
    """Returns a minimal valid transcript."""
    return Transcript(
        segments=(
            Segment(
                start=0.0,
                end=1.0,
                text="Hello.",
            ),
        ),
        language="ja",
    )


@pytest.fixture(autouse=True)
def isolate_state(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Isolates persistent state for every job test."""
    monkeypatch.setenv(
        "KOFFEE_STATE_DIR",
        str(tmp_path / "state"),
    )


def test_job_round_trip(tmp_path: Path) -> None:
    """Tests durable transcript storage and cleanup."""
    media = tmp_path / "movie.mp4"
    media.write_bytes(b"video")
    job = JobStore.open(
        media,
        KoffeeConfig(),
    )

    job.save_transcript(_transcript())

    job.close()
    reopened = JobStore.open(
        media,
        KoffeeConfig(),
    )
    assert reopened.load_transcript() == _transcript()

    reopened.delete()
    assert not reopened.directory.exists()


def test_checkpoint_excludes_api_key(
    tmp_path: Path,
) -> None:
    """Tests that credentials never enter job state."""
    media = tmp_path / "movie.mp4"
    media.write_bytes(b"video")

    job = JobStore.open(
        media,
        KoffeeConfig(
            translator="google",
            api_key="secret-value",
        ),
    )

    manifest_text = (job.directory / "manifest.json").read_text()
    assert "secret-value" not in manifest_text
    assert "api_key" not in json.loads(manifest_text)["saved_config"]


def test_changed_input_discards_stale_checkpoint(
    tmp_path: Path,
) -> None:
    """Tests that a changed input starts a fresh job instead of failing."""
    media = tmp_path / "movie.mp4"
    media.write_bytes(b"first")
    job = JobStore.open(media, KoffeeConfig())
    job.save_transcript(_transcript())

    job.close()
    media.write_bytes(b"second")
    reopened = JobStore.open(media, KoffeeConfig())

    assert reopened.load_transcript() is None
    assert reopened.manifest.fingerprint == fingerprint_input(media)


def test_fingerprint_uses_content(
    tmp_path: Path,
) -> None:
    """Tests sampled-content fingerprinting."""
    media = tmp_path / "movie.mp4"
    media.write_bytes(b"a" * 32)
    first = fingerprint_input(media)

    media.write_bytes(b"b" * 32)
    second = fingerprint_input(media)

    assert first.sample_digest != second.sample_digest


def test_second_writer_is_rejected_until_owner_closes(tmp_path: Path) -> None:
    """Tests a checkpoint permits only one live writer."""
    media = tmp_path / "movie.mp4"
    media.write_bytes(b"video")
    first = JobStore.open(media, KoffeeConfig())

    with pytest.raises(CheckpointLockedError):
        JobStore.open(media, KoffeeConfig())

    first.close()
    second = JobStore.open(media, KoffeeConfig())
    second.close()


def test_lock_survives_job_directory_deletion(tmp_path: Path) -> None:
    """Tests deleting checkpoint contents cannot release its lifetime lock."""
    media = tmp_path / "movie.mp4"
    media.write_bytes(b"video")
    job = JobStore.open(media, KoffeeConfig())
    job.delete()

    with pytest.raises(CheckpointLockedError):
        JobStore.open(media, KoffeeConfig())
    job.close()


def test_corrupt_manifest_raises_checkpoint_error(tmp_path: Path) -> None:
    """Tests malformed manifest JSON is translated to a checkpoint error."""
    media = tmp_path / "movie.mp4"
    media.write_bytes(b"video")
    job = JobStore.open(media, KoffeeConfig())
    manifest_path = job.directory / "manifest.json"
    job.close()
    manifest_path.write_text("{broken", encoding="utf-8")

    with pytest.raises(CheckpointCorruptError, match="manifest"):
        JobStore.open(media, KoffeeConfig())


def test_saved_chunk_rejects_start_entry_below_one() -> None:
    """Tests saved chunks use one-based subtitle entry identifiers."""
    segment = Segment(start=0.0, end=1.0, text="text")

    with pytest.raises(ValidationError, match="greater than or equal to 1"):
        SavedChunk(
            start_entry=0,
            source_segments=(segment,),
            translated_segments=(segment,),
            translator="google",
            translation_model="model",
        )


def test_saved_chunk_enforces_structure() -> None:
    """Tests saved chunks require nonempty aligned segments and timestamps."""
    source = Segment(start=0.0, end=1.0, text="source")
    translated = Segment(start=0.0, end=2.0, text="translated")

    with pytest.raises(ValidationError, match="timestamps"):
        SavedChunk(
            start_entry=1,
            source_segments=(source,),
            translated_segments=(translated,),
            translator="google",
            translation_model="model",
        )


def test_chunk_save_is_sequential_and_idempotent(tmp_path: Path) -> None:
    """Tests chunk persistence accepts identical replay but rejects gaps."""
    media = tmp_path / "movie.mp4"
    media.write_bytes(b"video")
    segment = Segment(start=0.0, end=1.0, text="text")
    chunk = SavedChunk(
        start_entry=1,
        source_segments=(segment,),
        translated_segments=(segment,),
        translator="google",
        translation_model="model",
    )
    gapped_chunk = SavedChunk(
        start_entry=3,
        source_segments=(segment,),
        translated_segments=(segment,),
        translator="google",
        translation_model="model",
    )
    with JobStore.open(media, KoffeeConfig()) as job:
        job.save_chunk(chunk)
        job.save_chunk(chunk)
        with pytest.raises(CheckpointChunkError, match="expected 2"):
            job.save_chunk(gapped_chunk)


def test_translation_settings_corruption_is_specific(tmp_path: Path) -> None:
    """Tests corrupt translation settings report checkpoint corruption."""
    media = tmp_path / "movie.mp4"
    media.write_bytes(b"video")
    with JobStore.open(media, KoffeeConfig()) as job:
        (job.directory / "translation.json").write_text("[]", encoding="utf-8")
        with pytest.raises(CheckpointCorruptError, match="translation settings"):
            job.prepare_translation(
                TranslationSettings(
                    source_language="ja",
                    target_language="en",
                    instructions_digest="digest",
                    chunk_size=1,
                    context_size=0,
                ),
                "google",
                "model",
                allow_mixed_translation=False,
            )


def test_provenance_validation_checks_every_chunk(tmp_path: Path) -> None:
    """Tests an early mixed-provenance chunk cannot hide behind the final chunk."""
    media = tmp_path / "movie.mp4"
    media.write_bytes(b"video")
    first = Segment(start=0.0, end=1.0, text="first")
    second = Segment(start=1.0, end=2.0, text="second")
    settings = TranslationSettings(
        source_language="ja",
        target_language="en",
        instructions_digest="digest",
        chunk_size=1,
        context_size=0,
    )
    with JobStore.open(media, KoffeeConfig()) as job:
        job.save_chunk(
            SavedChunk(
                start_entry=1,
                source_segments=(first,),
                translated_segments=(first,),
                translator="openai",
                translation_model="old",
            )
        )
        job.save_chunk(
            SavedChunk(
                start_entry=2,
                source_segments=(second,),
                translated_segments=(second,),
                translator="google",
                translation_model="model",
            )
        )
        with pytest.raises(CheckpointSettingsError, match="openai/old"):
            job.prepare_translation(
                settings,
                "google",
                "model",
                allow_mixed_translation=False,
            )
