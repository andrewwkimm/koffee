"""Tests for subtitle embedding."""

import subprocess
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from koffee.embed import _get_subtitle_codec, embed_subtitles
from koffee.exceptions import SubtitleEmbedError


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
    embed_subtitles(subtitle_file_path, video_file_path, output_file_path)

    assert output_file_path.exists()


def test_hard_overlay(
    video_file_path: Path, subtitle_file_path: Path, output_file_path: Path
) -> None:
    """Tests that hard burn-in produces an output file."""
    embed_subtitles(subtitle_file_path, video_file_path, output_file_path, mode="hard")

    assert output_file_path.exists()


def test_mkv_codec() -> None:
    """Tests that MKV files use the srt subtitle codec."""
    assert _get_subtitle_codec("output.mkv") == "srt"
    assert _get_subtitle_codec("output.webm") == "srt"
    assert _get_subtitle_codec("output.mp4") == "mov_text"


def test_exception_handling(
    subtitle_file_path: Path,
    video_file_path: Path,
    output_file_path: Path,
    mocker: MockerFixture,
) -> None:
    """Tests that exception is caught and an error is raised."""
    mocker.patch(
        "subprocess.run",
        side_effect=subprocess.CalledProcessError(
            returncode=1, cmd=["ffmpeg"], stderr="FFmpegError"
        ),
    )

    with pytest.raises(SubtitleEmbedError) as exc_info:
        embed_subtitles(subtitle_file_path, video_file_path, output_file_path)

    assert isinstance(exc_info.value.__cause__, subprocess.CalledProcessError)
    assert "FFmpegError" in str(exc_info.value)


def test_missing_ffmpeg_raises(
    subtitle_file_path: Path,
    video_file_path: Path,
    output_file_path: Path,
    mocker: MockerFixture,
) -> None:
    """Tests that missing ffmpeg raises FileNotFoundError."""
    mocker.patch(
        "subprocess.run",
        side_effect=FileNotFoundError,
    )

    with pytest.raises(FileNotFoundError):
        embed_subtitles(subtitle_file_path, video_file_path, output_file_path)


def test_timeout_raises(
    subtitle_file_path: Path,
    video_file_path: Path,
    output_file_path: Path,
    mocker: MockerFixture,
) -> None:
    """Tests that a timed-out ffmpeg raises TimeoutExpired."""
    mocker.patch(
        "subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd="ffmpeg", timeout=600),
    )

    with pytest.raises(subprocess.TimeoutExpired):
        embed_subtitles(subtitle_file_path, video_file_path, output_file_path)
