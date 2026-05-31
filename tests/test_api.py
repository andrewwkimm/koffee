"""Tests for the koffee API."""

import importlib
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

import koffee
from koffee.api import (
    _check_output_collision,
    _finalize_video_output,
    _get_output_path,
    _route_output,
    _translate,
    _validate_inputs,
    _write_output,
    run,
)
from koffee.exceptions import (
    IncompatibleOptionsError,
    InvalidVideoFileError,
    MissingApiKeyError,
    MissingDependencyError,
    UnsupportedFileError,
)
from koffee.schemas.config import KoffeeConfig
from koffee.schemas.types import Transcript


@pytest.fixture
def api_module():
    """Fixture to import the api module for mocking purposes."""
    return importlib.import_module("koffee.api")


@pytest.mark.integration
def test_api() -> None:
    """Tests if the API call successfully outputs a subtitle file."""
    video_path = Path("examples/videos/sample_korean_video.mp4")
    output_directory_path = Path("scratch")
    output_file_name = "python_output_video_file"

    output_file = koffee.run(
        input_path=video_path,
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
        koffee.run("invalid_file.mp4")


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


def test_translate_whisper_returns_raw_segments(mocker, api_module) -> None:
    """Tests that whisper backend uses raw segments without calling translate."""
    mock_translate = mocker.patch.object(api_module, "translate")
    mocker.patch.object(api_module, "generate_subtitles", return_value=MagicMock())
    config = MagicMock(spec=KoffeeConfig)
    config.provider = "whisper"
    config.subtitle_format = "srt"
    transcript: Transcript = {
        "segments": [{"start": 0.0, "end": 1.0, "text": "hi"}],
        "language": "en",
    }

    _translate(transcript, config, None)

    mock_translate.assert_not_called()


def test_translate_non_whisper_calls_translate(mocker, api_module) -> None:
    """Tests that a non-whisper backend calls translate."""
    mock_translate = mocker.patch.object(
        api_module, "translate", return_value=["translated"]
    )
    mocker.patch.object(api_module, "generate_subtitles", return_value=MagicMock())
    config = MagicMock(spec=KoffeeConfig)
    config.provider = "gemini"
    config.target_language = "en"
    config.api_key = None
    config.llm_model = "gemini-2.5-flash"
    config.chunk_size = None
    config.context_size = None
    config.sleep_requests = None
    config.prompt = None
    config.subtitle_format = "srt"
    transcript: Transcript = {"segments": [], "language": "ko"}

    _translate(transcript, config, None)

    mock_translate.assert_called_once_with(
        transcript,
        config.target_language,
        config.api_key,
        None,
        llm_model=config.llm_model,
        prompt=config.prompt,
        provider=config.provider,
        chunk_size=config.chunk_size,
        context_size=config.context_size,
        sleep_requests=config.sleep_requests,
    )


def test_finalize_video_output_deletes_subtitle(mocker, tmp_path, api_module) -> None:
    """Tests that the subtitle file is always deleted after embed."""
    mocker.patch.object(
        api_module, "embed_subtitles", return_value=tmp_path / "out.mp4"
    )
    subtitle = tmp_path / "sub.srt"
    subtitle.touch()

    _finalize_video_output(subtitle, tmp_path / "in.mp4", tmp_path / "out.mp4")

    assert not subtitle.exists()


def test_write_output_moves_subtitle_to_target(tmp_path) -> None:
    """Tests that `_write_output` moves the source to the resolved target path."""
    subtitle = tmp_path / "sub.srt"
    subtitle.touch()

    result = _write_output(
        subtitle, tmp_path / "track.mp4", "srt", None, None, overwrite=False
    )

    assert result == tmp_path / "track.srt"
    assert result.exists()
    assert not subtitle.exists()


def test_write_output_unlinks_source_on_collision(tmp_path) -> None:
    """Tests that a collision unlinks the source file before raising."""
    subtitle = tmp_path / "sub.srt"
    subtitle.touch()
    existing = tmp_path / "track.srt"
    existing.touch()

    with pytest.raises(FileExistsError, match="already exists"):
        _write_output(
            subtitle, tmp_path / "track.mp4", "srt", None, None, overwrite=False
        )

    assert not subtitle.exists()
    assert existing.exists()


def test_write_output_overwrites_when_allowed(tmp_path) -> None:
    """Tests that overwrite=True replaces an existing target."""
    subtitle = tmp_path / "sub.srt"
    subtitle.write_text("new")
    existing = tmp_path / "track.srt"
    existing.write_text("old")

    result = _write_output(
        subtitle, tmp_path / "track.mp4", "srt", None, None, overwrite=True
    )

    assert result.read_text() == "new"


def test_validate_api_key_raises_without_key() -> None:
    """Tests that an LLM backend without API key raises MissingApiKeyError."""
    with pytest.raises(MissingApiKeyError, match="API key is required"):
        koffee.run(
            "examples/videos/sample_korean_video.mp4",
            provider="gemini",
        )


def test_validate_api_key_ollama_does_not_require_key(tmp_path: Path) -> None:
    """Tests that ollama backend does not require an API key."""
    video = tmp_path / "video.mp4"
    video.touch()
    config = KoffeeConfig(provider="ollama", whisper_model="large-v3")
    try:
        _validate_inputs(str(video), config)
    except MissingApiKeyError:
        pytest.fail("ollama should not require an API key")
    except Exception:
        pass


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


def test_route_output_with_embed(mocker, api_module, tmp_path) -> None:
    """Tests that embed mode routes to video output."""
    subtitle = tmp_path / "sub.srt"
    subtitle.touch()
    mock_finalize = mocker.patch.object(
        api_module,
        "_finalize_video_output",
        return_value=tmp_path / "out.mp4",
    )
    mocker.patch.object(
        api_module, "_get_output_path", return_value=tmp_path / "out.mp4"
    )

    config = KoffeeConfig(embed="soft", overwrite=True)
    _route_output(Path("video.mp4"), subtitle, config)

    mock_finalize.assert_called_once()


def test_run_subtitle_file_input(mocker, api_module, tmp_path) -> None:
    """Tests that a subtitle file input skips ASR and translates directly."""
    srt = tmp_path / "test.srt"
    srt.write_text("1\n00:00:00,000 --> 00:00:01,000\nHello.\n")

    mock_parse = mocker.patch.object(
        api_module,
        "parse_subtitle_file",
        return_value=[{"start": 0.0, "end": 1.0, "text": "Hello."}],
    )
    mock_translate = mocker.patch.object(
        api_module,
        "translate",
        return_value=[{"start": 0.0, "end": 1.0, "text": "Translated."}],
    )
    mock_generate = mocker.patch.object(
        api_module,
        "generate_subtitles",
        return_value=tmp_path / "out.vtt",
    )
    mocker.patch("pathlib.Path.replace", return_value=tmp_path / "test.vtt")
    mocker.patch.object(api_module, "_check_output_collision")

    run(
        str(srt),
        config=KoffeeConfig(
            output_dir=tmp_path,
            provider="gemini",
            api_key="test-key",
            overwrite=True,
        ),
    )

    mock_parse.assert_called_once()
    mock_translate.assert_called_once()
    mock_generate.assert_called_once()


def test_validate_inputs_rejects_unsupported_suffix(tmp_path) -> None:
    """Tests that an unsupported file extension raises UnsupportedFileError."""
    bad_file = tmp_path / "notes.txt"
    bad_file.touch()

    with pytest.raises(UnsupportedFileError, match="Unsupported file type"):
        _validate_inputs(bad_file, KoffeeConfig())


def test_validate_inputs_rejects_embed_on_audio(tmp_path) -> None:
    """Tests that --embed on audio input raises IncompatibleOptionsError."""
    audio = tmp_path / "track.mp3"
    audio.touch()

    with pytest.raises(IncompatibleOptionsError, match="--embed is only supported"):
        _validate_inputs(audio, KoffeeConfig(embed="soft"))


def test_validate_inputs_rejects_embedded_subs_on_audio(tmp_path) -> None:
    """Tests that --use-embedded-subtitles on audio raises IncompatibleOptionsError."""
    audio = tmp_path / "track.mp3"
    audio.touch()

    with pytest.raises(
        IncompatibleOptionsError, match="--use-embedded-subtitles is only supported"
    ):
        _validate_inputs(audio, KoffeeConfig(use_embedded_subtitles=True))


def test_validate_inputs_rejects_missing_ffmpeg(mocker, tmp_path) -> None:
    """Tests that missing ffmpeg raises MissingDependencyError when embedding."""
    video = tmp_path / "clip.mp4"
    video.touch()
    mocker.patch("koffee.api.shutil.which", return_value=None)

    with pytest.raises(MissingDependencyError, match="ffmpeg was not found"):
        _validate_inputs(video, KoffeeConfig(embed="soft"))


def test_validate_inputs_rejects_no_embedded_tracks(mocker, tmp_path) -> None:
    """Tests that a video with no subtitle tracks raises IncompatibleOptionsError."""
    video = tmp_path / "clip.mp4"
    video.touch()
    mocker.patch("koffee.api.shutil.which", return_value="/usr/bin/ffmpeg")
    mocker.patch("koffee.api.get_subtitle_tracks", return_value=[])

    with pytest.raises(IncompatibleOptionsError, match="No embedded subtitle tracks"):
        _validate_inputs(video, KoffeeConfig(use_embedded_subtitles=True))


def test_validate_inputs_passes_on_valid_video(mocker, tmp_path) -> None:
    """Tests that a valid video file with a valid config passes validation."""
    video = tmp_path / "clip.mp4"
    video.touch()
    mocker.patch("koffee.api.shutil.which", return_value="/usr/bin/ffmpeg")

    _validate_inputs(video, KoffeeConfig(embed="soft"))


def test_validate_inputs_rejects_existing_output(tmp_path) -> None:
    """Tests that an existing output file raises FileExistsError upfront."""
    audio = tmp_path / "track.mp3"
    audio.touch()
    existing_output = tmp_path / "track.vtt"
    existing_output.touch()

    with pytest.raises(FileExistsError, match="Output file already exists"):
        _validate_inputs(audio, KoffeeConfig())


def test_validate_inputs_allows_existing_output_with_overwrite(tmp_path) -> None:
    """Tests that an existing output is tolerated when overwrite is enabled."""
    audio = tmp_path / "track.mp3"
    audio.touch()
    existing_output = tmp_path / "track.vtt"
    existing_output.touch()

    _validate_inputs(audio, KoffeeConfig(overwrite=True))


def test_validate_inputs_creates_missing_output_dir(tmp_path) -> None:
    """Tests that a missing output_dir is created during validation."""
    audio = tmp_path / "track.mp3"
    audio.touch()
    new_dir = tmp_path / "nested" / "out"

    _validate_inputs(audio, KoffeeConfig(output_dir=new_dir))

    assert new_dir.is_dir()


def test_validate_inputs_embed_checks_video_suffix_collision(mocker, tmp_path) -> None:
    """Tests that embed mode checks for collision against the video-suffix output."""
    video = tmp_path / "clip.mp4"
    video.touch()
    mocker.patch("koffee.api.shutil.which", return_value="/usr/bin/ffmpeg")
    colliding = tmp_path / f"clip_{datetime.now().strftime('%m-%d-%Y')}.mp4"
    colliding.touch()

    with pytest.raises(FileExistsError, match="Output file already exists"):
        _validate_inputs(video, KoffeeConfig(embed="soft"))


def test_write_output_audio_input_uses_audio_stem(tmp_path) -> None:
    """Tests that `_write_output` derives the stem from an audio input."""
    subtitle = tmp_path / "sub.srt"
    subtitle.touch()

    result = _write_output(
        subtitle, tmp_path / "track.mp3", "srt", None, None, overwrite=False
    )

    assert result == tmp_path / "track.srt"
    assert result.exists()
    assert not subtitle.exists()
