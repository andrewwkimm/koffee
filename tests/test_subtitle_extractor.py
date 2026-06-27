"""Tests for embedded subtitle detection and extraction."""

import json
import subprocess
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from koffee.subtitle import extract_subtitle_track, get_subtitle_tracks


def test_get_subtitle_tracks_returns_streams(mocker: MockerFixture) -> None:
    """Tests that subtitle tracks are parsed from ffprobe output."""
    ffprobe_output = json.dumps(
        {
            "streams": [
                {"index": 2, "tags": {"language": "jpn", "title": "Japanese"}},
            ]
        }
    )
    mocker.patch(
        "koffee.subtitle.subprocess.run",
        return_value=subprocess.CompletedProcess(
            args=[], returncode=0, stdout=ffprobe_output
        ),
    )

    result = get_subtitle_tracks("video.mkv")

    assert len(result) == 1
    assert result[0]["tags"]["language"] == "jpn"


def test_get_subtitle_tracks_no_streams(mocker: MockerFixture) -> None:
    """Tests that an empty list is returned when no subtitle tracks exist."""
    mocker.patch(
        "koffee.subtitle.subprocess.run",
        return_value=subprocess.CompletedProcess(
            args=[], returncode=0, stdout=json.dumps({"streams": []})
        ),
    )

    result = get_subtitle_tracks("video.mp4")

    assert result == []


def test_get_subtitle_tracks_missing_ffprobe(mocker: MockerFixture) -> None:
    """Tests that missing ffprobe raises FileNotFoundError."""
    mocker.patch(
        "koffee.subtitle.subprocess.run",
        side_effect=FileNotFoundError,
    )

    with pytest.raises(FileNotFoundError):
        get_subtitle_tracks("video.mkv")


def test_extract_subtitle_track(mocker: MockerFixture, tmp_path: Path) -> None:
    """Tests that a subtitle track is extracted to an SRT file."""
    video = tmp_path / "video.mkv"
    video.touch()
    expected_output = tmp_path / ".koffee_extracted_0.srt"

    mocker.patch(
        "koffee.subtitle.subprocess.run",
        return_value=subprocess.CompletedProcess(args=[], returncode=0),
    )

    result = extract_subtitle_track(video)

    assert result == expected_output


def test_extract_subtitle_track_failure(mocker: MockerFixture, tmp_path: Path) -> None:
    """Tests that extraction failure raises CalledProcessError."""
    video = tmp_path / "video.mkv"
    video.touch()

    mocker.patch(
        "koffee.subtitle.subprocess.run",
        side_effect=subprocess.CalledProcessError(1, "ffmpeg", stderr="error"),
    )

    with pytest.raises(subprocess.CalledProcessError):
        extract_subtitle_track(video)


def test_extract_subtitle_track_missing_ffmpeg(
    mocker: MockerFixture, tmp_path: Path
) -> None:
    """Tests that missing ffmpeg raises FileNotFoundError."""
    video = tmp_path / "video.mkv"
    video.touch()

    mocker.patch(
        "koffee.subtitle.subprocess.run",
        side_effect=FileNotFoundError,
    )

    with pytest.raises(FileNotFoundError):
        extract_subtitle_track(video)


def test_get_subtitle_tracks_timeout(mocker: MockerFixture) -> None:
    """Tests that a timed-out ffprobe raises TimeoutExpired."""
    mocker.patch(
        "koffee.subtitle.subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd="ffprobe", timeout=30),
    )

    with pytest.raises(subprocess.TimeoutExpired):
        get_subtitle_tracks("video.mkv")


def test_extract_subtitle_track_timeout(mocker: MockerFixture, tmp_path: Path) -> None:
    """Tests that a timed-out ffmpeg raises TimeoutExpired."""
    video = tmp_path / "video.mkv"
    video.touch()

    mocker.patch(
        "koffee.subtitle.subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd="ffmpeg", timeout=600),
    )

    with pytest.raises(subprocess.TimeoutExpired):
        extract_subtitle_track(video)
