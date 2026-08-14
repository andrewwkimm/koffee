"""Tests for persistent Koffee jobs."""

import json
from pathlib import Path

import pytest

from koffee.job import JobStore, fingerprint_input
from koffee.schemas.config import KoffeeConfig
from koffee.schemas.domain import Segment, Transcript


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


def test_job_round_trip(tmp_path: Path) -> None:
    """Tests durable transcript storage and cleanup."""
    media = tmp_path / "movie.mp4"
    media.write_bytes(b"video")
    job = JobStore.open(
        media,
        KoffeeConfig(),
    )

    job.save_transcript(_transcript())

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


def test_changed_input_is_rejected(
    tmp_path: Path,
) -> None:
    """Tests stale checkpoint rejection."""
    media = tmp_path / "movie.mp4"
    media.write_bytes(b"first")
    JobStore.open(media, KoffeeConfig())

    media.write_bytes(b"second")

    with pytest.raises(
        ValueError,
        match="input file changed",
    ):
        JobStore.open(media, KoffeeConfig())


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
