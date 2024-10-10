"""Tests for subtitle overlay."""

from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from koffee.exceptions import SubtitleOverlayError
from koffee.overlay import overlay_subtitles


@pytest.fixture
def video_file_path() -> Path:
    """Pytest fixture for the video file path."""
    return Path("examples/videos/sample_korean_video.mp4")


@pytest.fixture
def subtitle_file_path() -> Path:
    """Pytest fixture for the subtitles."""
    return Path("examples/subtitles/sample_srt_file.srt")


@pytest.fixture
def output_file_path() -> Path:
    """Pytest fixture for the output file path."""
    return Path("scratch/output_with_subtitles.mp4")


def test_overlay(
    video_file_path: Path, subtitle_file_path: Path, output_file_path: Path
) -> None:
    """Tests that the subtitle has been overlayed onto the video."""
    overlay_subtitles(subtitle_file_path, video_file_path, output_file_path)

    assert output_file_path.exists()


def test_exception_handling(
    subtitle_file_path: Path,
    video_file_path: Path,
    output_file_path: Path,
    mocker: MockerFixture,
) -> None:
    """Tests that exception is caught and an error is raised."""
    error = "FFmpegError"
    error_message = f"Subtitle overlaying failed: {error}"

    mocker.patch("ffmpeg.input", side_effect=Exception("FFmpegError"))

    with pytest.raises(SubtitleOverlayError) as exc_info:
        overlay_subtitles(subtitle_file_path, video_file_path, output_file_path)

    assert isinstance(exc_info.value.__cause__, Exception)
    assert error_message in str(exc_info.value)
