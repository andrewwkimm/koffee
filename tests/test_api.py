"""Tests for the koffee API."""

import importlib
from pathlib import Path
from unittest.mock import MagicMock

import pytest

import koffee
from koffee.data.config import KoffeeConfig
from koffee.exceptions import InvalidVideoFileError
from koffee.translate import (
    _apply_config_overrides,
    _check_output_collision,
    _finalize_video_output,
    _get_output_path,
    _get_segments,
    _handle_subtitle_output,
    _route_output,
    translate,
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
        overwrite=True,
    )

    assert Path(output_file).exists()
    assert Path(output_file).suffix in {".srt", ".vtt"}


def test_invalid_video_file() -> None:
    """Tests that the appropriate error is raised when an invalid file is given."""
    error_message = "Input file is not valid or does not exist."
    with pytest.raises(InvalidVideoFileError, match=error_message):
        koffee.translate("invalid_file.mp4")


def test_get_output_path_no_output_name() -> None:
    """Tests that files use the input stem when no output name is provided."""
    result = _get_output_path("video/track.mp3", output_dir=None, output_name=None)
    assert result.stem == "track"
    assert result.suffix == ".mp3"


def test_get_output_path_date_suffix() -> None:
    """Tests that date_suffix adds a date stamp to the filename."""
    result = _get_output_path(
        "video/track.mp4", output_dir=None, output_name=None, date_suffix=True
    )
    assert result.stem.startswith("track_")
    assert result.suffix == ".mp4"


def test_get_output_path_with_output_name() -> None:
    """Tests that a provided output name is used as-is."""
    result = _get_output_path("video/track.mp4", output_dir=None, output_name="custom")
    assert result.stem == "custom"


def test_get_output_path_with_output_dir() -> None:
    """Tests that a provided output directory is used."""
    result = _get_output_path(
        "video/track.mp4", output_dir=Path("/tmp"), output_name="custom"
    )
    assert result.parent == Path("/tmp")


def test_get_segments_whisper_returns_raw(mocker, translate_module) -> None:
    """Tests that whisper backend returns raw segments without translation."""
    mock_translate = mocker.patch.object(translate_module, "translate_transcript")
    config = MagicMock(spec=KoffeeConfig)
    config.translator = "whisper"
    transcript = {"segments": [{"start": 0.0, "end": 1.0, "text": "hi"}]}

    result = _get_segments(transcript, config)

    assert result == transcript["segments"]
    mock_translate.assert_not_called()


def test_get_segments_non_whisper_calls_translate(mocker, translate_module) -> None:
    """Tests that a non-whisper backend calls translate_transcript."""
    mock_translate = mocker.patch.object(
        translate_module, "translate_transcript", return_value=["translated"]
    )
    config = MagicMock(spec=KoffeeConfig)
    config.translator = "gemini"
    config.target_language = "en"
    config.api_key = None
    config.llm_model = "gemini-2.5-flash"
    config.prompt = None
    transcript = {"segments": [], "language": "ko"}

    result = _get_segments(transcript, config)

    assert result == ["translated"]
    mock_translate.assert_called_once_with(
        transcript,
        config.target_language,
        config.api_key,
        None,
        llm_model=config.llm_model,
        prompt=config.prompt,
        translator=config.translator,
    )


def test_finalize_video_output_deletes_subtitle(
    mocker, tmp_path, translate_module
) -> None:
    """Tests that the subtitle file is always deleted after overlay."""
    mocker.patch.object(
        translate_module, "overlay_subtitles", return_value=tmp_path / "out.mp4"
    )
    subtitle = tmp_path / "sub.srt"
    subtitle.touch()

    _finalize_video_output(subtitle, tmp_path / "in.mp4", tmp_path / "out.mp4")

    assert not subtitle.exists()


def test_handle_subtitle_output_renames_subtitle(tmp_path) -> None:
    """Tests that the subtitle file is moved to the correct output path."""
    subtitle = tmp_path / "sub.srt"
    subtitle.touch()
    output_path = tmp_path / "track.mp4"

    result = _handle_subtitle_output(subtitle, output_path, "srt")

    assert result == tmp_path / "track.srt"
    assert result.exists()
    assert not subtitle.exists()


def test_validate_api_key_raises_without_key() -> None:
    """Tests that an LLM backend without API key raises ValueError."""
    with pytest.raises(ValueError, match="API key is required"):
        koffee.translate(
            "examples/videos/sample_korean_video.mp4",
            translator="gemini",
        )


def test_apply_config_overrides_with_existing_config() -> None:
    """Tests that kwargs override fields on an existing config."""
    config = KoffeeConfig(target_language="en")
    result = _apply_config_overrides(config, {"target_language": "fr"})

    assert result.target_language == "fr"


def test_check_output_collision_raises(tmp_path) -> None:
    """Tests that an existing output file raises FileExistsError."""
    existing = tmp_path / "output.vtt"
    existing.touch()

    with pytest.raises(FileExistsError, match="already exists"):
        _check_output_collision(existing, overwrite=False)


def test_check_output_collision_allows_overwrite(tmp_path) -> None:
    """Tests that overwrite=True skips the collision check."""
    existing = tmp_path / "output.vtt"
    existing.touch()

    _check_output_collision(existing, overwrite=True)


def test_route_output_with_overlay(mocker, translate_module, tmp_path) -> None:
    """Tests that overlay mode routes to video output."""
    subtitle = tmp_path / "sub.srt"
    subtitle.touch()
    mock_finalize = mocker.patch.object(
        translate_module,
        "_finalize_video_output",
        return_value=tmp_path / "out.mp4",
    )
    mocker.patch.object(
        translate_module, "_get_output_path", return_value=tmp_path / "out.mp4"
    )

    config = KoffeeConfig(overlay="soft", overwrite=True)
    _route_output(Path("video.mp4"), subtitle, config)

    mock_finalize.assert_called_once()


def test_translate_subtitle_file_input(mocker, translate_module, tmp_path) -> None:
    """Tests that a subtitle file input skips ASR and translates directly."""
    srt = tmp_path / "test.srt"
    srt.write_text("1\n00:00:00,000 --> 00:00:01,000\nHello.\n")

    mock_parse = mocker.patch.object(
        translate_module,
        "parse_subtitle_file",
        return_value=[{"start": 0.0, "end": 1.0, "text": "Hello."}],
    )
    mock_translate = mocker.patch.object(
        translate_module,
        "translate_transcript",
        return_value=[{"start": 0.0, "end": 1.0, "text": "Translated."}],
    )
    mock_generate = mocker.patch.object(
        translate_module,
        "generate_subtitles",
        return_value=tmp_path / "out.vtt",
    )
    mocker.patch("pathlib.Path.replace", return_value=tmp_path / "test.vtt")
    mocker.patch.object(translate_module, "_check_output_collision")

    translate(
        str(srt),
        config=KoffeeConfig(
            output_dir=tmp_path,
            translator="gemini",
            api_key="test-key",
            overwrite=True,
        ),
    )

    mock_parse.assert_called_once()
    mock_translate.assert_called_once()
    mock_generate.assert_called_once()


def test_handle_subtitle_output_audio_renames_subtitle(tmp_path) -> None:
    """Tests that the subtitle file is moved correctly for audio inputs."""
    subtitle = tmp_path / "sub.srt"
    subtitle.touch()
    output_path = tmp_path / "track.mp3"

    result = _handle_subtitle_output(subtitle, output_path, "srt")

    assert result == tmp_path / "track.srt"
    assert result.exists()
    assert not subtitle.exists()
