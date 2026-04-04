"""Tests for the koffee API."""

import importlib
from pathlib import Path
from unittest.mock import MagicMock

import pytest

import koffee
from koffee.data.config import KoffeeConfig
from koffee.exceptions import InvalidVideoFileError
from koffee.translate import (
    _finalize_video_output,
    _get_output_path,
    _get_segments,
    _handle_subtitle_output,
)


@pytest.fixture
def translate_module():
    """Fixture to import the translate module for mocking purposes."""
    return importlib.import_module("koffee.translate")


@pytest.mark.integration
def test_api() -> None:
    """Tests if the API call successfully outputs a subtitle file."""
    video_file_path = Path("examples/videos/sample_korean_video.mp4")
    output_directory_path = Path("scratch")
    output_file_name = "python_output_video_file"

    output_file = koffee.translate(
        video_file_path=video_file_path,
        output_dir=output_directory_path,
        output_name=output_file_name,
        compute_type="int8",
    )

    assert Path(output_file).exists()
    assert Path(output_file).suffix in {".srt", ".vtt"}


def test_invalid_video_file() -> None:
    """Tests that the appropriate error is raised when an invalid file is given."""
    error_message = "Inputted file is not a valid video file or does not exist."
    with pytest.raises(InvalidVideoFileError, match=error_message):
        koffee.translate("invalid_file.mp4")


def test_get_output_path_audio_no_output_name() -> None:
    """Test that audio files use the stem as the output name when none is provided."""
    result = _get_output_path("video/track.mp3", output_dir=None, output_name=None)
    assert result.name == "track.mp3"


def test_get_output_path_with_output_name() -> None:
    """Test that a provided output name is used as-is."""
    result = _get_output_path("video/track.mp4", output_dir=None, output_name="custom")
    assert result.stem == "custom"


def test_get_output_path_with_output_dir() -> None:
    """Test that a provided output directory is used."""
    result = _get_output_path(
        "video/track.mp4", output_dir=Path("/tmp"), output_name="custom"
    )
    assert result.parent == Path("/tmp")


def test_get_segments_whisper_returns_raw(mocker, translate_module) -> None:
    """Test that whisper backend returns raw segments without translation."""
    mock_translate = mocker.patch.object(translate_module, "translate_transcript")
    config = MagicMock(spec=KoffeeConfig)
    config.translation_backend = "whisper"
    transcript = {"segments": [{"start": 0.0, "end": 1.0, "text": "hi"}]}

    result = _get_segments(transcript, config)

    assert result == transcript["segments"]
    mock_translate.assert_not_called()


def test_get_segments_non_whisper_calls_translate(mocker, translate_module) -> None:
    """Test that a non-whisper backend calls translate_transcript."""
    mock_translate = mocker.patch.object(
        translate_module, "translate_transcript", return_value=["translated"]
    )
    config = MagicMock(spec=KoffeeConfig)
    config.translation_backend = "gemini"
    config.target_language = "en"
    config.api_key = None
    transcript = {"segments": [], "language": "ko"}

    result = _get_segments(transcript, config)

    assert result == ["translated"]
    mock_translate.assert_called_once_with(
        transcript, config.target_language, config.api_key
    )


def test_finalize_video_output_deletes_subtitle(
    mocker, tmp_path, translate_module
) -> None:
    """Test that the subtitle file is always deleted after overlay."""
    mocker.patch.object(
        translate_module, "overlay_subtitles", return_value=tmp_path / "out.mp4"
    )
    subtitle = tmp_path / "sub.srt"
    subtitle.touch()

    _finalize_video_output(subtitle, tmp_path / "in.mp4", tmp_path / "out.mp4")

    assert not subtitle.exists()


def test_handle_subtitle_output_renames_subtitle(tmp_path) -> None:
    """Test that the subtitle file is moved to the correct output path."""
    subtitle = tmp_path / "sub.srt"
    subtitle.touch()
    output_path = tmp_path / "track.mp4"

    result = _handle_subtitle_output(subtitle, output_path, "srt")

    assert result == tmp_path / "track.srt"
    assert result.exists()
    assert not subtitle.exists()


def test_handle_subtitle_output_audio_renames_subtitle(tmp_path) -> None:
    """Test that the subtitle file is moved correctly for audio inputs."""
    subtitle = tmp_path / "sub.srt"
    subtitle.touch()
    output_path = tmp_path / "track.mp3"

    result = _handle_subtitle_output(subtitle, output_path, "srt")

    assert result == tmp_path / "track.srt"
    assert result.exists()
    assert not subtitle.exists()
