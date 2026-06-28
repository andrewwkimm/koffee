"""Tests for subtitle embedding."""

import subprocess
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from koffee.embed import (
    _escape_subtitle_filter_path,
    _ffmpeg_supports_subtitles_filter,
    embed_subtitles,
)
from koffee.exceptions import SubtitleEmbedError


@pytest.fixture
def video_path() -> Path:
    """Pytest fixture for the video file path."""
    return Path("examples/videos/sample_korean_video.mp4")


@pytest.fixture
def subtitle_path() -> Path:
    """Pytest fixture for the subtitles."""
    return Path("examples/subtitles/sample_srt_file.srt")


@pytest.fixture
def output_path(tmp_path: Path) -> Path:
    """Pytest fixture for the output file path."""
    return tmp_path / "output_with_subtitles.mp4"


@pytest.mark.integration
def test_overlay(video_path: Path, subtitle_path: Path, output_path: Path) -> None:
    """Tests that the subtitle has been overlayed onto the video."""
    embed_subtitles(subtitle_path, video_path, output_path)

    assert output_path.exists()


@pytest.mark.integration
def test_hard_overlay(video_path: Path, subtitle_path: Path, output_path: Path) -> None:
    """Tests that hard burn-in produces an output file."""
    embed_subtitles(subtitle_path, video_path, output_path, mode="hard")

    assert output_path.exists()


def test_burn_in_without_libass_raises_helpful_error(
    subtitle_path: Path,
    video_path: Path,
    output_path: Path,
    mocker: MockerFixture,
) -> None:
    """Tests that burn-in without the libass filter raises a descriptive error."""
    mocker.patch("koffee.embed._ffmpeg_supports_subtitles_filter", return_value=False)

    with pytest.raises(SubtitleEmbedError) as exc_info:
        embed_subtitles(subtitle_path, video_path, output_path, mode="hard")

    assert "libass" in str(exc_info.value)
    assert "ffmpeg-full" in str(exc_info.value)


def test_ffmpeg_supports_subtitles_filter_when_present(mocker: MockerFixture) -> None:
    """Tests that the subtitles filter is detected in ffmpeg -filters output."""
    mocker.patch(
        "subprocess.run",
        return_value=subprocess.CompletedProcess(
            args=["ffmpeg"],
            returncode=0,
            stdout=" T.. subtitles    V->V  Render text subtitles onto input video.\n",
            stderr="",
        ),
    )

    assert _ffmpeg_supports_subtitles_filter() is True


def test_ffmpeg_supports_subtitles_filter_when_absent(mocker: MockerFixture) -> None:
    """Tests that a missing subtitles filter is detected in ffmpeg -filters output."""
    mocker.patch(
        "subprocess.run",
        return_value=subprocess.CompletedProcess(
            args=["ffmpeg"],
            returncode=0,
            stdout=" ... scale          V->V  Scale the input video size.\n",
            stderr="",
        ),
    )

    assert _ffmpeg_supports_subtitles_filter() is False


def test_exception_handling(
    subtitle_path: Path,
    video_path: Path,
    output_path: Path,
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
        embed_subtitles(subtitle_path, video_path, output_path)

    assert isinstance(exc_info.value.__cause__, subprocess.CalledProcessError)
    assert "FFmpegError" in str(exc_info.value)


def test_missing_ffmpeg_raises(
    subtitle_path: Path,
    video_path: Path,
    output_path: Path,
    mocker: MockerFixture,
) -> None:
    """Tests that missing ffmpeg raises FileNotFoundError."""
    mocker.patch(
        "subprocess.run",
        side_effect=FileNotFoundError,
    )

    with pytest.raises(FileNotFoundError):
        embed_subtitles(subtitle_path, video_path, output_path)


def test_escape_subtitle_filter_path_windows_drive() -> None:
    """Tests that a Windows drive path is normalized and the colon escaped."""
    assert (
        _escape_subtitle_filter_path("C:\\Users\\me\\sub.srt")
        == "C\\:/Users/me/sub.srt"
    )


def test_escape_subtitle_filter_path_metacharacters() -> None:
    """Tests that filter-graph metacharacters are backslash-escaped."""
    result = _escape_subtitle_filter_path("/tmp/a,b[c]d;e'f.srt")
    assert result == "/tmp/a\\,b\\[c\\]d\\;e\\'f.srt"


def test_burn_in_subtitles_uses_escaped_path(
    video_path: Path,
    output_path: Path,
    mocker: MockerFixture,
) -> None:
    """Tests that `_burn_in_subtitles` passes an escaped path to ffmpeg."""
    mocker.patch("koffee.embed._ffmpeg_supports_subtitles_filter", return_value=True)
    mock_run = mocker.patch("subprocess.run")

    embed_subtitles("C:\\subs\\track.srt", video_path, output_path, mode="hard")

    cmd = mock_run.call_args[0][0]
    vf_index = cmd.index("-vf")
    assert cmd[vf_index + 1] == "subtitles=C\\:/subs/track.srt"


def test_timeout_raises(
    subtitle_path: Path,
    video_path: Path,
    output_path: Path,
    mocker: MockerFixture,
) -> None:
    """Tests that a timed-out ffmpeg raises TimeoutExpired."""
    mocker.patch(
        "subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd="ffmpeg", timeout=600),
    )

    with pytest.raises(subprocess.TimeoutExpired):
        embed_subtitles(subtitle_path, video_path, output_path)
