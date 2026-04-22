"""Tests for CLI."""

import logging
import subprocess
import sys
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from koffee.cli import (
    _find_config_path,
    _handle_embedded_subtitles,
    _resolve_paths,
    _select_subtitle_track,
    cli,
    convert,
    embed,
    info,
    languages,
    tracks,
    transcribe,
)
from koffee.data.config import LANGUAGE_CODES, KoffeeConfig

korean_video_file_path = Path("examples/videos/sample_korean_video.mp4")

output_directory_path = Path("scratch")
output_file_name = "cli_output_video_file"


def test_cli(mocker: MockerFixture) -> None:
    """Tests that CLI processes a valid video file."""
    mock_translate = mocker.patch("koffee.cli.run")

    cli(
        korean_video_file_path,
        compute_type="int8",
        output_dir=output_directory_path,
        output_stem=output_file_name,
    )

    mock_translate.assert_called_once()
    config = mock_translate.call_args.kwargs["config"]

    assert config.compute_type == "int8"
    assert config.output_dir == output_directory_path
    assert config.output_stem == output_file_name


def test_script_run() -> None:
    """Tests that the CLI script runs."""
    cli_path = Path("koffee/cli.py")
    result = subprocess.run(
        [sys.executable, cli_path], check=False, capture_output=True, text=True
    )

    assert result.returncode == 0


def test_embed_soft(mocker: MockerFixture) -> None:
    """Tests that embed flag is passed through to config."""
    mock_translate = mocker.patch("koffee.cli.run")

    cli(
        korean_video_file_path,
        compute_type="int8",
        output_dir=output_directory_path,
        output_stem=output_file_name,
        embed="soft",
    )

    mock_translate.assert_called_once()
    config = mock_translate.call_args.kwargs["config"]

    assert config.embed == "soft"


def test_embed_defaults_to_none(mocker: MockerFixture) -> None:
    """Tests that embed defaults to none."""
    mock_translate = mocker.patch("koffee.cli.run")

    cli(
        korean_video_file_path,
        compute_type="int8",
        output_dir=output_directory_path,
        output_stem=output_file_name,
    )

    mock_translate.assert_called_once()
    config = mock_translate.call_args.kwargs["config"]

    assert config.embed == "none"


def test_verbose(mocker: MockerFixture) -> None:
    """Tests if verbose flag sets log level to DEBUG."""
    mocker.patch("koffee.cli.run")
    mock_logger = mocker.patch("logging.getLogger")
    logger_instance = mock_logger.return_value

    cli(
        korean_video_file_path,
        compute_type="int8",
        output_dir=output_directory_path,
        output_stem=output_file_name,
        verbose=True,
    )

    logger_instance.setLevel.assert_called_once_with(logging.DEBUG)


def test_resolve_paths_expands_directory(tmp_path) -> None:
    """Tests that a directory input resolves to supported files within it."""
    (tmp_path / "video.mp4").touch()
    (tmp_path / "audio.wav").touch()
    (tmp_path / "readme.txt").touch()

    result = _resolve_paths((tmp_path,))

    suffixes = {p.suffix for p in result}
    assert suffixes == {".mp4", ".wav"}
    assert len(result) == 2


def test_resolve_paths_glob_pattern(tmp_path, monkeypatch) -> None:
    """Tests that glob patterns resolve to matching files."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "a.mp4").touch()
    (tmp_path / "b.mp4").touch()

    result = _resolve_paths((Path("*.mp4"),))

    assert len(result) == 2


def test_resolve_paths_glob_no_match(tmp_path, monkeypatch) -> None:
    """Tests that unmatched glob patterns pass through as-is."""
    monkeypatch.chdir(tmp_path)

    result = _resolve_paths((Path("nonexistent*.mp4"),))

    assert len(result) == 1
    assert result[0] == Path("nonexistent*.mp4")


def test_dry_run(mocker: MockerFixture) -> None:
    """Tests that dry-run previews actions without translating."""
    mock_translate = mocker.patch("koffee.cli.run")
    mocker.patch("koffee.cli.get_subtitle_tracks", return_value=[])

    cli(
        korean_video_file_path,
        output_dir=output_directory_path,
        dry_run=True,
    )

    mock_translate.assert_not_called()


def test_dry_run_subtitle_file(mocker: MockerFixture, tmp_path) -> None:
    """Tests that dry-run shows subtitle translation mode for .srt files."""
    mock_translate = mocker.patch("koffee.cli.run")
    mocker.patch("koffee.cli.get_subtitle_tracks", return_value=[])
    srt = tmp_path / "test.srt"
    srt.touch()

    cli(srt, dry_run=True)

    mock_translate.assert_not_called()


def test_dry_run_with_embed(mocker: MockerFixture) -> None:
    """Tests that dry-run shows embed info when flag is set."""
    mocker.patch("koffee.cli.run")
    mocker.patch("koffee.cli.get_subtitle_tracks", return_value=[])

    cli(
        korean_video_file_path,
        output_dir=output_directory_path,
        dry_run=True,
        embed="soft",
    )


def test_handle_embedded_subtitles_skips_subtitle_files(
    tmp_path,
) -> None:
    """Tests that subtitle files skip the embedded subtitle check."""
    srt = tmp_path / "test.srt"
    srt.touch()
    config = KoffeeConfig()

    result = _handle_embedded_subtitles(srt, config)

    assert result.use_embedded_subtitles is False


def test_handle_embedded_subtitles_no_tracks(
    mocker: MockerFixture,
) -> None:
    """Tests that videos with no subtitle tracks return config unchanged."""
    mocker.patch("koffee.cli.get_subtitle_tracks", return_value=[])
    config = KoffeeConfig()

    result = _handle_embedded_subtitles(korean_video_file_path, config)

    assert result.use_embedded_subtitles is False


def test_handle_embedded_subtitles_user_accepts(
    mocker: MockerFixture,
) -> None:
    """Tests that accepting embedded subtitles updates config."""
    tracks = [{"index": 0, "codec": "srt", "tags": {"language": "ko"}}]
    mocker.patch("koffee.cli.get_subtitle_tracks", return_value=tracks)
    mocker.patch("builtins.input", return_value="y")
    config = KoffeeConfig()

    result = _handle_embedded_subtitles(korean_video_file_path, config)

    assert result.use_embedded_subtitles is True
    assert result.source_language == "ko"


def test_handle_embedded_subtitles_user_declines(
    mocker: MockerFixture,
) -> None:
    """Tests that declining embedded subtitles keeps config unchanged."""
    mocker.patch(
        "koffee.cli.get_subtitle_tracks",
        return_value=[{"index": 0, "codec": "srt"}],
    )
    mocker.patch("builtins.input", return_value="n")
    config = KoffeeConfig()

    result = _handle_embedded_subtitles(korean_video_file_path, config)

    assert result.use_embedded_subtitles is False


def test_translate_with_progress_subtitle_file(mocker: MockerFixture, tmp_path) -> None:
    """Tests that subtitle files skip the ASR progress bar."""
    mock_translate = mocker.patch("koffee.cli.run")
    mocker.patch("koffee.cli.get_subtitle_tracks", return_value=[])
    srt = tmp_path / "test.srt"
    srt.touch()

    cli(srt, output_dir=output_directory_path)

    mock_translate.assert_called_once()
    call_kwargs = mock_translate.call_args.kwargs
    assert "on_asr_progress" not in call_kwargs
    assert call_kwargs["on_translate_progress"] is not None


def test_batch_progress_logging(mocker: MockerFixture) -> None:
    """Tests that batch processing logs progress for multiple files."""
    mock_translate = mocker.patch("koffee.cli.run")
    mocker.patch("koffee.cli.get_subtitle_tracks", return_value=[])
    mock_log = mocker.patch("koffee.cli.log")

    cli(
        korean_video_file_path,
        korean_video_file_path,
        output_dir=output_directory_path,
    )

    assert mock_translate.call_count == 2
    log_messages = [call.args[0] for call in mock_log.info.call_args_list]
    assert any("[1/2]" in msg for msg in log_messages)
    assert any("[2/2]" in msg for msg in log_messages)


def test_batch_summary_on_success(mocker: MockerFixture) -> None:
    """Tests that batch processing logs a summary when all files succeed."""
    mocker.patch("koffee.cli.run")
    mocker.patch("koffee.cli.get_subtitle_tracks", return_value=[])
    mock_log = mocker.patch("koffee.cli.log")

    cli(
        korean_video_file_path,
        korean_video_file_path,
        output_dir=output_directory_path,
    )

    log_messages = [call.args[0] for call in mock_log.info.call_args_list]
    assert any("2/2 succeeded" in msg for msg in log_messages)


def test_batch_summary_on_partial_failure(mocker: MockerFixture) -> None:
    """Tests that batch processing logs failed files in the summary."""
    mocker.patch("koffee.cli.run", side_effect=[None, ValueError("boom")])
    mocker.patch("koffee.cli.get_subtitle_tracks", return_value=[])
    mock_log = mocker.patch("koffee.cli.log")

    cli(
        korean_video_file_path,
        korean_video_file_path,
        output_dir=output_directory_path,
    )

    info_messages = [call.args[0] for call in mock_log.info.call_args_list]
    error_messages = [call.args[0] for call in mock_log.error.call_args_list]
    assert any("1/2 succeeded" in msg for msg in info_messages)
    assert any("failed" in msg for msg in info_messages)
    assert any("boom" in msg for msg in error_messages)


def test_prompt_flag(mocker: MockerFixture) -> None:
    """Tests that --prompt is passed through to config."""
    mock_translate = mocker.patch("koffee.cli.run")
    mocker.patch("koffee.cli.get_subtitle_tracks", return_value=[])

    cli(
        korean_video_file_path,
        output_dir=output_directory_path,
        prompt="You are a medical translator.",
    )

    mock_translate.assert_called_once()
    config = mock_translate.call_args.kwargs["config"]
    assert config.prompt == "You are a medical translator."


def test_config_flag_loads_file(mocker: MockerFixture, tmp_path) -> None:
    """Tests that --config loads the specified config file."""
    config_file = tmp_path / "custom.toml"
    config_file.write_text('target_language = "fr"\n')

    mock_translate = mocker.patch("koffee.cli.run")
    mocker.patch("koffee.cli.get_subtitle_tracks", return_value=[])

    cli(
        korean_video_file_path,
        config=config_file,
        output_dir=output_directory_path,
    )

    mock_translate.assert_called_once()
    used_config = mock_translate.call_args.kwargs["config"]
    assert used_config.target_language == "fr"


def test_select_subtitle_track_single() -> None:
    """Tests that a single track is selected automatically."""
    tracks = [{"index": 0, "tags": {"language": "ja"}}]

    index, lang = _select_subtitle_track(tracks)

    assert index == 0
    assert lang == "ja"


def test_select_subtitle_track_multiple(mocker: MockerFixture) -> None:
    """Tests that user can select from multiple tracks."""
    tracks = [
        {"index": 0, "tags": {"language": "ja", "title": "Japanese"}},
        {"index": 1, "tags": {"language": "ko", "title": "Korean"}},
    ]
    mocker.patch("builtins.input", return_value="1")

    index, lang = _select_subtitle_track(tracks)

    assert index == 1
    assert lang == "ko"


def test_select_subtitle_track_default_on_empty_input(mocker: MockerFixture) -> None:
    """Tests that empty input defaults to track 0."""
    tracks = [
        {"index": 0, "tags": {"language": "ja"}},
        {"index": 1, "tags": {"language": "ko"}},
    ]
    mocker.patch("builtins.input", return_value="")

    index, lang = _select_subtitle_track(tracks)

    assert index == 0
    assert lang == "ja"


def test_select_subtitle_track_missing_language_tag() -> None:
    """Tests that a track without language tag returns None."""
    track_list = [{"index": 0, "tags": {}}]

    index, lang = _select_subtitle_track(track_list)

    assert index == 0
    assert lang is None


def test_info_command(mocker: MockerFixture) -> None:
    """Tests that info command runs without error."""
    mocker.patch("koffee.cli.shutil.which", return_value="/usr/bin/ffmpeg")
    mocker.patch(
        "koffee.cli.subprocess.run",
        return_value=subprocess.CompletedProcess(
            args=[], returncode=0, stdout="ffmpeg version 7.0\n"
        ),
    )

    info()


def test_info_command_no_ffmpeg(mocker: MockerFixture) -> None:
    """Tests that info command handles missing ffmpeg."""
    mocker.patch("koffee.cli.shutil.which", return_value=None)

    info()


def test_tracks_command(mocker: MockerFixture) -> None:
    """Tests that tracks command lists subtitle tracks."""
    mocker.patch(
        "koffee.cli.get_subtitle_tracks",
        return_value=[
            {"index": 0, "tags": {"language": "ja", "title": "Japanese"}},
            {"index": 1, "tags": {"language": "en"}},
        ],
    )

    tracks(korean_video_file_path)


def test_tracks_command_no_tracks(mocker: MockerFixture) -> None:
    """Tests that tracks command handles no subtitle tracks."""
    mocker.patch("koffee.cli.get_subtitle_tracks", return_value=[])

    tracks(korean_video_file_path)


def test_find_config_path_returns_none(monkeypatch) -> None:
    """Tests that _find_config_path returns None when no config exists."""
    monkeypatch.setattr(
        "koffee.cli.CONFIG_SEARCH_PATHS",
        [Path("/nonexistent/koffee.toml")],
    )

    assert _find_config_path() is None


def test_embed_command(mocker: MockerFixture, tmp_path) -> None:
    """Tests that embed command calls embed_subtitles."""
    video = tmp_path / "video.mp4"
    video.touch()
    sub = tmp_path / "sub.srt"
    sub.touch()
    output = tmp_path / "out.mp4"

    mock_embed = mocker.patch("koffee.cli.embed_subtitles", return_value=output)

    embed(video, sub, output_path=output)

    mock_embed.assert_called_once_with(sub, video, output, mode="soft")


def test_embed_command_hard_mode(mocker: MockerFixture, tmp_path) -> None:
    """Tests that embed command passes hard mode."""
    video = tmp_path / "video.mp4"
    video.touch()
    sub = tmp_path / "sub.srt"
    sub.touch()
    output = tmp_path / "out.mp4"

    mock_embed = mocker.patch("koffee.cli.embed_subtitles", return_value=output)

    embed(video, sub, output_path=output, mode="hard")

    mock_embed.assert_called_once_with(sub, video, output, mode="hard")


def test_embed_command_default_output(mocker: MockerFixture, tmp_path) -> None:
    """Tests that embed generates a default output name."""
    video = tmp_path / "video.mp4"
    video.touch()
    sub = tmp_path / "sub.srt"
    sub.touch()
    expected_output = tmp_path / "video_embed.mp4"

    mock_embed = mocker.patch(
        "koffee.cli.embed_subtitles", return_value=expected_output
    )

    embed(video, sub)

    mock_embed.assert_called_once_with(sub, video, expected_output, mode="soft")


def test_embed_command_collision(tmp_path) -> None:
    """Tests that embed raises FileExistsError without --overwrite."""
    video = tmp_path / "video.mp4"
    video.touch()
    sub = tmp_path / "sub.srt"
    sub.touch()
    output = tmp_path / "out.mp4"
    output.touch()

    with pytest.raises(FileExistsError, match="already exists"):
        embed(video, sub, output_path=output)


def test_transcribe_command(mocker: MockerFixture, tmp_path) -> None:
    """Tests that transcribe command runs ASR and generates subtitles."""
    audio = tmp_path / "audio.mp3"
    audio.touch()
    subtitle_file = tmp_path / "generated.vtt"
    subtitle_file.touch()

    mocker.patch(
        "koffee.cli.asr.transcribe",
        return_value={
            "segments": [{"start": 0.0, "end": 1.0, "text": "Hello."}],
            "language": "en",
        },
    )
    mocker.patch(
        "koffee.cli.generate_subtitles",
        return_value=subtitle_file,
    )
    mocker.patch("pathlib.Path.replace")

    transcribe(audio, output_dir=tmp_path, output_stem="output")


def test_transcribe_command_collision(mocker: MockerFixture, tmp_path) -> None:
    """Tests that transcribe raises FileExistsError without --overwrite."""
    audio = tmp_path / "audio.mp3"
    audio.touch()
    existing = tmp_path / "audio.vtt"
    existing.touch()
    subtitle_file = tmp_path / "generated.vtt"
    subtitle_file.touch()

    mocker.patch(
        "koffee.cli.asr.transcribe",
        return_value={
            "segments": [{"start": 0.0, "end": 1.0, "text": "Hello."}],
            "language": "en",
        },
    )
    mocker.patch(
        "koffee.cli.generate_subtitles",
        return_value=subtitle_file,
    )

    with pytest.raises(FileExistsError, match="already exists"):
        transcribe(audio, output_dir=tmp_path)


def test_convert_command(mocker: MockerFixture, tmp_path) -> None:
    """Tests that convert command parses and regenerates subtitles."""
    srt = tmp_path / "test.srt"
    srt.write_text("1\n00:00:00,000 --> 00:00:01,000\nHello.\n")
    subtitle_file = tmp_path / "generated.vtt"
    subtitle_file.touch()

    mock_parse = mocker.patch(
        "koffee.cli.parse_subtitle_file",
        return_value=[{"start": 0.0, "end": 1.0, "text": "Hello."}],
    )
    mocker.patch(
        "koffee.cli.generate_subtitles",
        return_value=subtitle_file,
    )
    mocker.patch("pathlib.Path.replace")

    convert(srt, subtitle_format="vtt", output_dir=tmp_path, output_stem="output")

    mock_parse.assert_called_once_with(srt)


def test_convert_command_default_output(mocker: MockerFixture, tmp_path) -> None:
    """Tests that convert uses the input filename as default output name."""
    srt = tmp_path / "test.srt"
    srt.write_text("1\n00:00:00,000 --> 00:00:01,000\nHello.\n")
    subtitle_file = tmp_path / "generated.vtt"
    subtitle_file.touch()

    mocker.patch(
        "koffee.cli.parse_subtitle_file",
        return_value=[{"start": 0.0, "end": 1.0, "text": "Hello."}],
    )
    mocker.patch(
        "koffee.cli.generate_subtitles",
        return_value=subtitle_file,
    )
    mocker.patch("pathlib.Path.replace")

    convert(srt, subtitle_format="vtt", output_dir=tmp_path)


def test_convert_command_collision(mocker: MockerFixture, tmp_path) -> None:
    """Tests that convert raises FileExistsError without --overwrite."""
    srt = tmp_path / "test.srt"
    srt.write_text("1\n00:00:00,000 --> 00:00:01,000\nHello.\n")
    existing = tmp_path / "test.vtt"
    existing.touch()
    subtitle_file = tmp_path / "generated.vtt"
    subtitle_file.touch()

    mocker.patch(
        "koffee.cli.parse_subtitle_file",
        return_value=[{"start": 0.0, "end": 1.0, "text": "Hello."}],
    )
    mocker.patch(
        "koffee.cli.generate_subtitles",
        return_value=subtitle_file,
    )

    with pytest.raises(FileExistsError, match="already exists"):
        convert(srt, subtitle_format="vtt", output_dir=tmp_path)


def test_languages_command(capsys) -> None:
    """Tests that languages command prints all supported language codes."""
    languages()

    captured = capsys.readouterr()
    codes = sorted(LANGUAGE_CODES - {"auto"})
    for code in codes:
        assert code in captured.out


def test_languages_command_shows_count(capsys) -> None:
    """Tests that languages command displays the total count."""
    languages()

    captured = capsys.readouterr()
    expected_count = len(LANGUAGE_CODES - {"auto"})
    assert str(expected_count) in captured.out


def test_languages_command_excludes_auto(capsys) -> None:
    """Tests that languages command excludes the 'auto' pseudo-language."""
    languages()

    captured = capsys.readouterr()
    assert "auto" not in captured.out.split()


def test_languages_command_shows_names(capsys) -> None:
    """Tests that languages command displays full language names."""
    languages()

    captured = capsys.readouterr()
    assert "ko (Korean)" in captured.out
    assert "en (English)" in captured.out
    assert "ja (Japanese)" in captured.out
