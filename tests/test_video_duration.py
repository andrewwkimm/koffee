"""Tests for get_video_duration utility."""

import subprocess

import pytest

from koffee.asr import _get_video_duration as get_video_duration


def test_returns_duration(mocker) -> None:
    """Tests that a valid ffprobe output is parsed as a float."""
    expected_duration = 123.45
    mocker.patch(
        "subprocess.run",
        return_value=subprocess.CompletedProcess(
            args=[], returncode=0, stdout=f"{expected_duration}\n"
        ),
    )
    assert get_video_duration("video.mp4") == expected_duration


def test_empty_stdout_returns_zero(mocker) -> None:
    """Tests that empty ffprobe output returns 0.0."""
    mocker.patch(
        "subprocess.run",
        return_value=subprocess.CompletedProcess(args=[], returncode=0, stdout=""),
    )
    assert get_video_duration("video.mp4") == 0.0


def test_missing_ffprobe_raises(mocker) -> None:
    """Tests that a missing ffprobe raises FileNotFoundError."""
    mocker.patch(
        "subprocess.run",
        side_effect=FileNotFoundError,
    )
    with pytest.raises(FileNotFoundError):
        get_video_duration("video.mp4")


def test_timeout_raises(mocker) -> None:
    """Tests that a timed-out ffprobe raises TimeoutExpired."""
    mocker.patch(
        "subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd="ffprobe", timeout=30),
    )
    with pytest.raises(subprocess.TimeoutExpired):
        get_video_duration("video.mp4")
