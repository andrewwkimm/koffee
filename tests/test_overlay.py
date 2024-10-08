"""Tests for subtitle overlay."""

from pathlib import Path

import pytest

from koffee.overlay import overlay_subtitles


@pytest.fixture
def video_file_path() -> Path:
    """Pytest fixture for the video file path."""
    return Path("examples/videos/sample_korean_video.mp4")


@pytest.fixture
def srt_file_path() -> Path:
    """Pytest fixture for the SRT file."""
    return Path("examples/subtitles/sample_srt_file.srt")


@pytest.fixture
def output_file_path() -> Path:
    """Pytest fixture for the output file path."""
    return Path("scratch/output_with_subtitles.mp4")


def test_overlay(
    video_file_path: Path, srt_file_path: Path, output_file_path: Path
) -> None:
    """Tests that the subtitle has been overlayed onto the video."""
    overlay_subtitles(video_file_path, srt_file_path, output_file_path)

    assert output_file_path.exists()

    output_file_path.unlink
