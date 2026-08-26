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
                {
                    "index": 2,
                    "codec_name": "subrip",
                    "tags": {"language": "jpn", "title": "Japanese"},
                },
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
    expected_absolute_stream_index = 2
    assert result[0].absolute_stream_index == expected_absolute_stream_index
    assert result[0].subtitle_ordinal == 0
    assert result[0].codec_name == "subrip"
    assert result[0].language == "jpn"


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


def test_extract_subtitle_track(
    mocker: MockerFixture,
    tmp_path: Path,
) -> None:
    """Tests extraction into the caller-owned output directory."""
    video = tmp_path / "video.mkv"
    video.touch()
    output_dir = tmp_path / "temporary"
    expected_output = output_dir / "embedded_subtitle_0.srt"
    mock_run = mocker.patch(
        "koffee.subtitle.subprocess.run",
        return_value=subprocess.CompletedProcess(
            args=[],
            returncode=0,
        ),
    )

    result = extract_subtitle_track(
        video,
        subtitle_ordinal=0,
        output_dir=output_dir,
    )

    assert result == expected_output
    assert output_dir.is_dir()
    assert str(expected_output) in mock_run.call_args.args[0]


def test_extract_subtitle_track_accepts_legacy_track_index(
    mocker: MockerFixture,
    tmp_path: Path,
) -> None:
    """Tests that the legacy keyword selects the same subtitle ordinal."""
    mock_run = mocker.patch(
        "koffee.subtitle.subprocess.run",
        return_value=subprocess.CompletedProcess(args=[], returncode=0),
    )

    result = extract_subtitle_track(
        tmp_path / "video.mkv",
        output_dir=tmp_path,
        track_index=2,
    )

    assert result == tmp_path / "embedded_subtitle_2.srt"
    assert "0:s:2" in mock_run.call_args.args[0]


def test_extract_subtitle_track_rejects_conflicting_track_selectors(
    tmp_path: Path,
) -> None:
    """Tests that conflicting current and legacy selectors are rejected."""
    with pytest.raises(
        ValueError,
        match="subtitle_ordinal and legacy track_index cannot both select",
    ):
        extract_subtitle_track(
            tmp_path / "video.mkv",
            subtitle_ordinal=1,
            track_index=2,
        )


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


def test_get_subtitle_tracks_filters_bitmap_codecs_without_renumbering(
    mocker: MockerFixture,
) -> None:
    """Tests that text tracks retain their original subtitle ordinals."""
    ffprobe_output = json.dumps(
        {
            "streams": [
                {"index": 2, "codec_name": "hdmv_pgs_subtitle"},
                {"index": 5, "codec_name": "subrip", "tags": {"language": "eng"}},
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
    expected_absolute_stream_index = 5
    assert result[0].absolute_stream_index == expected_absolute_stream_index
    assert result[0].subtitle_ordinal == 1
