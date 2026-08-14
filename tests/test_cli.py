"""Tests for CLI."""

import logging
import subprocess
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from koffee.cli.commands import (
    _find_config_path,
    _resolve_paths,
    cli,
    convert,
    embed,
    info,
    languages,
    tracks,
    transcribe,
)
from koffee.cli.embedded import (
    _handle_embedded_subtitles,
    _select_subtitle_track,
)
from koffee.exceptions import IncompatibleOptionsError, KoffeeError, TranslationError
from koffee.schemas.config import LANGUAGE_CODES, KoffeeConfig
from koffee.schemas.domain import Segment, SubtitleTrack, Transcript

korean_video_path = Path("examples/videos/sample_korean_video.mp4")

output_directory_path = Path("scratch")
output_file_name = "cli_output_video_file"


def test_cli(mocker: MockerFixture) -> None:
    """Tests that CLI processes a valid video file."""
    mock_translate = mocker.patch("koffee.cli.commands.run")

    cli(
        korean_video_path,
        compute_type="int8",
        output_dir=output_directory_path,
        output_name=output_file_name,
    )

    mock_translate.assert_called_once()
    config = mock_translate.call_args.kwargs["config"]

    assert config.compute_type == "int8"
    assert config.output_dir == output_directory_path
    assert config.output_name == output_file_name


def test_embed_soft(mocker: MockerFixture) -> None:
    """Tests that embed flag is passed through to config."""
    mock_translate = mocker.patch("koffee.cli.commands.run")

    cli(
        korean_video_path,
        compute_type="int8",
        output_dir=output_directory_path,
        output_name=output_file_name,
        embed="soft",
    )

    mock_translate.assert_called_once()
    config = mock_translate.call_args.kwargs["config"]

    assert config.embed == "soft"


def test_embed_defaults_to_none(mocker: MockerFixture) -> None:
    """Tests that embed defaults to none."""
    mock_translate = mocker.patch("koffee.cli.commands.run")

    cli(
        korean_video_path,
        compute_type="int8",
        output_dir=output_directory_path,
        output_name=output_file_name,
    )

    mock_translate.assert_called_once()
    config = mock_translate.call_args.kwargs["config"]

    assert config.embed == "none"


def test_verbose(mocker: MockerFixture) -> None:
    """Tests that the verbose flag sets log level to DEBUG."""
    mocker.patch("koffee.cli.commands.run")
    mock_logger = mocker.patch("logging.getLogger")
    logger_instance = mock_logger.return_value

    cli(
        korean_video_path,
        compute_type="int8",
        output_dir=output_directory_path,
        output_name=output_file_name,
        verbose=True,
    )

    logger_instance.setLevel.assert_called_once_with(logging.DEBUG)


def test_resolve_paths_expands_directory(tmp_path: Path) -> None:
    """Tests that a directory input resolves to supported files within it."""
    (tmp_path / "video.mp4").touch()
    (tmp_path / "audio.wav").touch()
    (tmp_path / "subtitles.srt").touch()
    (tmp_path / "readme.txt").touch()

    result = _resolve_paths((tmp_path,))

    suffixes = {p.suffix for p in result}
    assert suffixes == {".mp4", ".wav", ".srt"}
    expected_file_count = 3
    assert len(result) == expected_file_count


def test_resolve_paths_glob_pattern(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Tests that glob patterns resolve to matching files."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "a.mp4").touch()
    (tmp_path / "b.mp4").touch()

    result = _resolve_paths((Path("*.mp4"),))

    expected_match_count = 2
    assert len(result) == expected_match_count


def test_resolve_paths_glob_no_match(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Tests that unmatched glob patterns raise FileNotFoundError."""
    monkeypatch.chdir(tmp_path)

    with pytest.raises(FileNotFoundError, match="nonexistent"):
        _resolve_paths((Path("nonexistent*.mp4"),))


def test_dry_run(mocker: MockerFixture) -> None:
    """Tests that dry-run previews actions without translating."""
    mock_translate = mocker.patch("koffee.cli.commands.run")
    mocker.patch("koffee.cli.embedded.get_subtitle_tracks", return_value=[])

    cli(
        korean_video_path,
        output_dir=output_directory_path,
        dry_run=True,
    )

    mock_translate.assert_not_called()


def test_dry_run_subtitle_file(mocker: MockerFixture, tmp_path: Path) -> None:
    """Tests that dry-run shows subtitle translation mode for .srt files."""
    mock_translate = mocker.patch("koffee.cli.commands.run")
    mocker.patch("koffee.cli.embedded.get_subtitle_tracks", return_value=[])
    srt = tmp_path / "test.srt"
    srt.touch()

    cli(srt, dry_run=True)

    mock_translate.assert_not_called()


def test_dry_run_with_embed(mocker: MockerFixture) -> None:
    """Tests that dry-run reports embed info when the flag is set."""
    mock_translate = mocker.patch("koffee.cli.commands.run")
    mocker.patch("koffee.cli.embedded.get_subtitle_tracks", return_value=[])
    mock_log = mocker.patch("koffee.cli.commands.log")

    cli(
        korean_video_path,
        output_dir=output_directory_path,
        dry_run=True,
        embed="soft",
    )

    mock_translate.assert_not_called()
    log_messages = [call.args[0] for call in mock_log.info.call_args_list]
    assert any("embedded" in msg for msg in log_messages)


def test_handle_embedded_subtitles_skips_subtitle_files(
    tmp_path: Path,
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
    mocker.patch("koffee.cli.embedded.get_subtitle_tracks", return_value=[])
    config = KoffeeConfig()

    result = _handle_embedded_subtitles(korean_video_path, config)

    assert result.use_embedded_subtitles is False


def test_handle_embedded_subtitles_user_accepts(
    mocker: MockerFixture,
) -> None:
    """Tests that accepting embedded subtitles updates config."""
    track_list = [SubtitleTrack(index=0, language="ko", title=None)]
    mocker.patch("koffee.cli.embedded.get_subtitle_tracks", return_value=track_list)
    mocker.patch("builtins.input", return_value="y")
    config = KoffeeConfig()

    result = _handle_embedded_subtitles(korean_video_path, config)

    assert result.use_embedded_subtitles is True
    assert result.source_language == "ko"


def test_handle_embedded_subtitles_user_declines(
    mocker: MockerFixture,
) -> None:
    """Tests that declining embedded subtitles keeps config unchanged."""
    mocker.patch(
        "koffee.cli.embedded.get_subtitle_tracks",
        return_value=[{"index": 0, "codec": "srt"}],
    )
    mocker.patch("builtins.input", return_value="n")
    config = KoffeeConfig()

    result = _handle_embedded_subtitles(korean_video_path, config)

    assert result.use_embedded_subtitles is False


def test_translate_with_progress_subtitle_file(
    mocker: MockerFixture, tmp_path: Path
) -> None:
    """Tests that subtitle files skip the ASR progress bar."""
    mock_translate = mocker.patch("koffee.cli.commands.run")
    mocker.patch("koffee.cli.embedded.get_subtitle_tracks", return_value=[])
    srt = tmp_path / "test.srt"
    srt.touch()

    cli(srt, output_dir=output_directory_path)

    mock_translate.assert_called_once()
    call_kwargs = mock_translate.call_args.kwargs
    assert "on_asr_progress" not in call_kwargs
    assert call_kwargs["on_translate_progress"] is not None


def test_batch_progress_logging(mocker: MockerFixture) -> None:
    """Tests that batch processing logs progress for multiple files."""
    mock_translate = mocker.patch("koffee.cli.commands.run")
    mocker.patch("koffee.cli.embedded.get_subtitle_tracks", return_value=[])
    mock_log = mocker.patch("koffee.cli.commands.log")

    cli(
        korean_video_path,
        korean_video_path,
        output_dir=output_directory_path,
    )

    expected_file_count = 2
    assert mock_translate.call_count == expected_file_count
    log_messages = [call.args[0] for call in mock_log.info.call_args_list]
    assert any("[1/2]" in msg for msg in log_messages)
    assert any("[2/2]" in msg for msg in log_messages)


def test_batch_summary_on_success(mocker: MockerFixture) -> None:
    """Tests that batch processing logs a summary when all files succeed."""
    mocker.patch("koffee.cli.commands.run")
    mocker.patch("koffee.cli.embedded.get_subtitle_tracks", return_value=[])
    mock_log = mocker.patch("koffee.cli.commands.log")

    cli(
        korean_video_path,
        korean_video_path,
        output_dir=output_directory_path,
    )

    log_messages = [call.args[0] for call in mock_log.info.call_args_list]
    assert any("2/2 succeeded" in msg for msg in log_messages)


def test_batch_summary_on_partial_failure(mocker: MockerFixture) -> None:
    """Tests that batch processing logs failed files in the summary."""
    mocker.patch("koffee.cli.commands.run", side_effect=[None, KoffeeError("boom")])
    mocker.patch("koffee.cli.embedded.get_subtitle_tracks", return_value=[])
    mock_log = mocker.patch("koffee.cli.commands.log")

    cli(
        korean_video_path,
        korean_video_path,
        output_dir=output_directory_path,
    )

    info_messages = [call.args[0] for call in mock_log.info.call_args_list]
    error_messages = [call.args[0] for call in mock_log.error.call_args_list]
    assert any("1/2 succeeded" in msg for msg in info_messages)
    assert any("failed" in msg for msg in info_messages)
    assert any("boom" in msg for msg in error_messages)


def test_translation_failure_prompt_yes_saves(mocker: MockerFixture) -> None:
    """Tests that answering yes at the prompt triggers a transcription save."""
    mocker.patch(
        "koffee.cli.commands.run", side_effect=TranslationError("boom", segments=[])
    )
    mocker.patch("koffee.cli.embedded.get_subtitle_tracks", return_value=[])
    mock_save = mocker.patch("koffee.cli.commands._save_raw_transcription")
    mocker.patch("koffee.cli.commands.Confirm.ask", return_value=True)
    mocker.patch("koffee.cli.commands.sys.stdin.isatty", return_value=True)

    cli(korean_video_path, output_dir=output_directory_path)

    mock_save.assert_called_once()


def test_translation_failure_prompt_no_does_not_save(mocker: MockerFixture) -> None:
    """Tests that answering no at the prompt skips the save."""
    mocker.patch(
        "koffee.cli.commands.run", side_effect=TranslationError("boom", segments=[])
    )
    mocker.patch("koffee.cli.embedded.get_subtitle_tracks", return_value=[])
    mock_save = mocker.patch("koffee.cli.commands._save_raw_transcription")
    mocker.patch("koffee.cli.commands.Confirm.ask", return_value=False)
    mocker.patch("koffee.cli.commands.sys.stdin.isatty", return_value=True)

    cli(
        korean_video_path,
        korean_video_path,
        output_dir=output_directory_path,
    )

    mock_save.assert_not_called()


def test_translation_failure_save_skips_prompt(mocker: MockerFixture) -> None:
    """Tests that --on-translation-failure=save bypasses the prompt entirely."""
    mocker.patch(
        "koffee.cli.commands.run", side_effect=TranslationError("boom", segments=[])
    )
    mocker.patch("koffee.cli.embedded.get_subtitle_tracks", return_value=[])
    mock_save = mocker.patch("koffee.cli.commands._save_raw_transcription")
    mock_confirm = mocker.patch("koffee.cli.commands.Confirm.ask")

    cli(
        korean_video_path,
        output_dir=output_directory_path,
        on_translation_failure="save",
    )

    mock_confirm.assert_not_called()
    mock_save.assert_called_once()


def test_translation_failure_abort_skips_prompt_and_save(mocker: MockerFixture) -> None:
    """Tests that --on-translation-failure=abort skips both the prompt and the save."""
    mocker.patch(
        "koffee.cli.commands.run", side_effect=TranslationError("boom", segments=[])
    )
    mocker.patch("koffee.cli.embedded.get_subtitle_tracks", return_value=[])
    mock_save = mocker.patch("koffee.cli.commands._save_raw_transcription")
    mock_confirm = mocker.patch("koffee.cli.commands.Confirm.ask")

    cli(
        korean_video_path,
        output_dir=output_directory_path,
        on_translation_failure="abort",
    )

    mock_confirm.assert_not_called()
    mock_save.assert_not_called()


def test_translation_failure_non_tty_falls_back_to_save(mocker: MockerFixture) -> None:
    """Tests that a non-TTY stdin auto-saves instead of attempting a prompt."""
    mocker.patch(
        "koffee.cli.commands.run", side_effect=TranslationError("boom", segments=[])
    )
    mocker.patch("koffee.cli.embedded.get_subtitle_tracks", return_value=[])
    mock_save = mocker.patch("koffee.cli.commands._save_raw_transcription")
    mock_confirm = mocker.patch("koffee.cli.commands.Confirm.ask")
    mocker.patch("koffee.cli.commands.sys.stdin.isatty", return_value=False)

    cli(korean_video_path, output_dir=output_directory_path)

    mock_confirm.assert_not_called()
    mock_save.assert_called_once()


def test_batch_continues_after_translation_failure(mocker: MockerFixture) -> None:
    """Tests that a translation failure on one file does not stop later files."""
    mock_run = mocker.patch(
        "koffee.cli.commands.run",
        side_effect=[TranslationError("boom", segments=[]), None, None],
    )
    mocker.patch("koffee.cli.embedded.get_subtitle_tracks", return_value=[])
    mocker.patch("koffee.cli.commands._save_raw_transcription")
    mocker.patch("koffee.cli.commands.Confirm.ask", return_value=True)
    mocker.patch("koffee.cli.commands.sys.stdin.isatty", return_value=True)

    cli(
        korean_video_path,
        korean_video_path,
        korean_video_path,
        output_dir=output_directory_path,
    )

    expected_file_count = 3
    assert mock_run.call_count == expected_file_count


def test_prompt_flag(mocker: MockerFixture) -> None:
    """Tests that --prompt is passed through to config."""
    mock_translate = mocker.patch("koffee.cli.commands.run")
    mocker.patch("koffee.cli.embedded.get_subtitle_tracks", return_value=[])

    cli(
        korean_video_path,
        output_dir=output_directory_path,
        prompt="You are a medical translator.",
    )

    mock_translate.assert_called_once()
    config = mock_translate.call_args.kwargs["config"]
    assert config.prompt == "You are a medical translator."


def test_config_flag_loads_file(mocker: MockerFixture, tmp_path: Path) -> None:
    """Tests that --config loads the specified config file."""
    config_file = tmp_path / "custom.toml"
    config_file.write_text('target_language = "fr"\n')

    mock_translate = mocker.patch("koffee.cli.commands.run")
    mocker.patch("koffee.cli.embedded.get_subtitle_tracks", return_value=[])

    cli(
        korean_video_path,
        config=config_file,
        output_dir=output_directory_path,
    )

    mock_translate.assert_called_once()
    used_config = mock_translate.call_args.kwargs["config"]
    assert used_config.target_language == "fr"


def test_select_subtitle_track_single() -> None:
    """Tests that a single track is selected automatically."""
    track_list = [SubtitleTrack(index=0, language="ja", title=None)]

    index, lang = _select_subtitle_track(track_list)

    assert index == 0
    assert lang == "ja"


def test_select_subtitle_track_multiple(mocker: MockerFixture) -> None:
    """Tests that user can select from multiple tracks."""
    track_list = [
        SubtitleTrack(index=0, language="ja", title="Japanese"),
        SubtitleTrack(index=1, language="ko", title="Korean"),
    ]
    mocker.patch("builtins.input", return_value="1")

    index, lang = _select_subtitle_track(track_list)

    assert index == 1
    assert lang == "ko"


def test_select_subtitle_track_default_on_empty_input(mocker: MockerFixture) -> None:
    """Tests that empty input defaults to track 0."""
    track_list = [
        SubtitleTrack(index=0, language="ja", title=None),
        SubtitleTrack(index=1, language="ko", title=None),
    ]
    mocker.patch("builtins.input", return_value="")

    index, lang = _select_subtitle_track(track_list)

    assert index == 0
    assert lang == "ja"


def test_select_subtitle_track_missing_language_tag() -> None:
    """Tests that a track without language tag returns None."""
    track_list = [SubtitleTrack(index=0, language=None, title=None)]

    index, lang = _select_subtitle_track(track_list)

    assert index == 0
    assert lang is None


def test_info_command(mocker: MockerFixture) -> None:
    """Tests that info command reports the ffmpeg version when present."""
    mocker.patch("koffee.cli.commands.shutil.which", return_value="/usr/bin/ffmpeg")
    mocker.patch(
        "koffee.cli.commands.subprocess.run",
        return_value=subprocess.CompletedProcess(
            args=[], returncode=0, stdout="ffmpeg version 7.0\n"
        ),
    )
    mock_log = mocker.patch("koffee.cli.commands.log")

    info()

    log_messages = [call.args[0] for call in mock_log.info.call_args_list]
    assert any("ffmpeg version 7.0" in msg for msg in log_messages)


def test_info_command_no_ffmpeg(mocker: MockerFixture) -> None:
    """Tests that info command reports ffmpeg as not found when missing."""
    mocker.patch("koffee.cli.commands.shutil.which", return_value=None)
    mock_log = mocker.patch("koffee.cli.commands.log")

    info()

    log_messages = [call.args[0] for call in mock_log.info.call_args_list]
    assert any("ffmpeg: not found" in msg for msg in log_messages)


def test_tracks_command(mocker: MockerFixture) -> None:
    """Tests that tracks command lists each subtitle track."""
    mocker.patch(
        "koffee.cli.commands.get_subtitle_tracks",
        return_value=[
            SubtitleTrack(index=0, language="ja", title="Japanese"),
            SubtitleTrack(index=1, language="en", title=None),
        ],
    )
    mock_log = mocker.patch("koffee.cli.commands.log")

    tracks(korean_video_path)

    log_messages = [call.args[0] for call in mock_log.info.call_args_list]
    assert any("[0] ja" in msg and "Japanese" in msg for msg in log_messages)
    assert any("[1] en" in msg for msg in log_messages)


def test_tracks_command_no_tracks(mocker: MockerFixture) -> None:
    """Tests that tracks command reports when no subtitle tracks are found."""
    mocker.patch("koffee.cli.commands.get_subtitle_tracks", return_value=[])
    mock_log = mocker.patch("koffee.cli.commands.log")

    tracks(korean_video_path)

    log_messages = [call.args[0] for call in mock_log.info.call_args_list]
    assert any("No subtitle tracks found" in msg for msg in log_messages)


def test_find_config_path_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tests that _find_config_path returns None when no config exists."""
    monkeypatch.setattr(
        "koffee.cli.commands.CONFIG_SEARCH_PATHS",
        [Path("/nonexistent/koffee.toml")],
    )

    assert _find_config_path() is None


def test_embed_command(mocker: MockerFixture, tmp_path: Path) -> None:
    """Tests that embed command calls embed_subtitles."""
    video = tmp_path / "video.mp4"
    video.touch()
    sub = tmp_path / "sub.srt"
    sub.touch()
    output = tmp_path / "out.mp4"

    mock_embed = mocker.patch(
        "koffee.cli.commands.embed_subtitles", return_value=output
    )

    embed(video, sub, output_path=output)

    mock_embed.assert_called_once_with(sub, video, output, mode="soft")


def test_embed_command_hard_mode(mocker: MockerFixture, tmp_path: Path) -> None:
    """Tests that embed command passes hard mode."""
    video = tmp_path / "video.mp4"
    video.touch()
    sub = tmp_path / "sub.srt"
    sub.touch()
    output = tmp_path / "out.mp4"

    mock_embed = mocker.patch(
        "koffee.cli.commands.embed_subtitles", return_value=output
    )

    embed(video, sub, output_path=output, mode="hard")

    mock_embed.assert_called_once_with(sub, video, output, mode="hard")


def test_embed_command_default_output(mocker: MockerFixture, tmp_path: Path) -> None:
    """Tests that embed generates a default output name."""
    video = tmp_path / "video.mp4"
    video.touch()
    sub = tmp_path / "sub.srt"
    sub.touch()
    expected_output = tmp_path / "video_embed.mp4"

    mock_embed = mocker.patch(
        "koffee.cli.commands.embed_subtitles", return_value=expected_output
    )

    embed(video, sub)

    mock_embed.assert_called_once_with(sub, video, expected_output, mode="soft")


def test_embed_command_collision(tmp_path: Path) -> None:
    """Tests that embed raises FileExistsError without --overwrite."""
    video = tmp_path / "video.mp4"
    video.touch()
    sub = tmp_path / "sub.srt"
    sub.touch()
    output = tmp_path / "out.mp4"
    output.touch()

    with pytest.raises(FileExistsError, match="already exists"):
        embed(video, sub, output_path=output)


def test_transcribe_command(mocker: MockerFixture, tmp_path: Path) -> None:
    """Tests that transcribe command runs ASR and generates subtitles."""
    audio = tmp_path / "audio.mp3"
    audio.touch()
    subtitle_file = tmp_path / "generated.vtt"
    subtitle_file.touch()

    mocker.patch(
        "koffee.cli.commands.asr.transcribe",
        return_value=Transcript(
            segments=[Segment(start=0.0, end=1.0, text="Hello.")], language="en"
        ),
    )
    mocker.patch(
        "koffee.cli.commands.generate_subtitles",
        return_value=subtitle_file,
    )
    mocker.patch("pathlib.Path.replace")

    transcribe(audio, output_dir=tmp_path, output_name="output")


def test_transcribe_command_collision(mocker: MockerFixture, tmp_path: Path) -> None:
    """Tests that transcribe raises FileExistsError without --overwrite."""
    audio = tmp_path / "audio.mp3"
    audio.touch()
    existing = tmp_path / "audio.vtt"
    existing.touch()
    subtitle_file = tmp_path / "generated.vtt"
    subtitle_file.touch()

    mocker.patch(
        "koffee.cli.commands.asr.transcribe",
        return_value=Transcript(
            segments=[Segment(start=0.0, end=1.0, text="Hello.")], language="en"
        ),
    )
    mocker.patch(
        "koffee.cli.commands.generate_subtitles",
        return_value=subtitle_file,
    )

    with pytest.raises(FileExistsError, match="already exists"):
        transcribe(audio, output_dir=tmp_path)


def test_convert_command(mocker: MockerFixture, tmp_path: Path) -> None:
    """Tests that convert command parses and regenerates subtitles."""
    srt = tmp_path / "test.srt"
    srt.write_text("1\n00:00:00,000 --> 00:00:01,000\nHello.\n")
    subtitle_file = tmp_path / "generated.vtt"
    subtitle_file.touch()

    mock_parse = mocker.patch(
        "koffee.cli.commands.parse_subtitle_file",
        return_value=[Segment(start=0.0, end=1.0, text="Hello.")],
    )
    mocker.patch(
        "koffee.cli.commands.generate_subtitles",
        return_value=subtitle_file,
    )
    mocker.patch("pathlib.Path.replace")

    convert(srt, subtitle_format="vtt", output_dir=tmp_path, output_name="output")

    mock_parse.assert_called_once_with(srt)


def test_convert_command_default_output(mocker: MockerFixture, tmp_path: Path) -> None:
    """Tests that convert uses the input filename as default output name."""
    srt = tmp_path / "test.srt"
    srt.write_text("1\n00:00:00,000 --> 00:00:01,000\nHello.\n")
    subtitle_file = tmp_path / "generated.vtt"
    subtitle_file.touch()

    mocker.patch(
        "koffee.cli.commands.parse_subtitle_file",
        return_value=[Segment(start=0.0, end=1.0, text="Hello.")],
    )
    mocker.patch(
        "koffee.cli.commands.generate_subtitles",
        return_value=subtitle_file,
    )
    mocker.patch("pathlib.Path.replace")

    convert(srt, subtitle_format="vtt", output_dir=tmp_path)


def test_convert_command_collision(mocker: MockerFixture, tmp_path: Path) -> None:
    """Tests that convert raises FileExistsError without --overwrite."""
    srt = tmp_path / "test.srt"
    srt.write_text("1\n00:00:00,000 --> 00:00:01,000\nHello.\n")
    existing = tmp_path / "test.vtt"
    existing.touch()
    subtitle_file = tmp_path / "generated.vtt"
    subtitle_file.touch()

    mocker.patch(
        "koffee.cli.commands.parse_subtitle_file",
        return_value=[Segment(start=0.0, end=1.0, text="Hello.")],
    )
    mocker.patch(
        "koffee.cli.commands.generate_subtitles",
        return_value=subtitle_file,
    )

    with pytest.raises(FileExistsError, match="already exists"):
        convert(srt, subtitle_format="vtt", output_dir=tmp_path)


def test_languages_command(capsys: pytest.CaptureFixture[str]) -> None:
    """Tests that languages command prints all supported language codes."""
    languages()

    captured = capsys.readouterr()
    codes = sorted(LANGUAGE_CODES - {"auto"})
    for code in codes:
        assert code in captured.out


def test_languages_command_shows_count(capsys: pytest.CaptureFixture[str]) -> None:
    """Tests that languages command displays the total count."""
    languages()

    captured = capsys.readouterr()
    expected_count = len(LANGUAGE_CODES - {"auto"})
    assert str(expected_count) in captured.out


def test_languages_command_excludes_auto(capsys: pytest.CaptureFixture[str]) -> None:
    """Tests that languages command excludes the 'auto' pseudo-language."""
    languages()

    captured = capsys.readouterr()
    assert "auto" not in captured.out.split()


def test_languages_command_shows_names(capsys: pytest.CaptureFixture[str]) -> None:
    """Tests that languages command displays full language names."""
    languages()

    captured = capsys.readouterr()
    assert "ko (Korean)" in captured.out
    assert "en (English)" in captured.out
    assert "ja (Japanese)" in captured.out


def test_batch_keeps_per_file_embedded_configuration(
    mocker: MockerFixture,
    tmp_path: Path,
) -> None:
    """Tests that embedded-track choices remain isolated by input."""
    first = tmp_path / "first.mkv"
    second = tmp_path / "second.mkv"
    first.touch()
    second.touch()
    embedded_config = KoffeeConfig(
        use_embedded_subtitles=True,
        subtitle_track_index=2,
    )
    asr_config = KoffeeConfig()
    mocker.patch(
        "koffee.cli.commands._handle_embedded_subtitles",
        side_effect=[embedded_config, asr_config],
    )
    mock_run = mocker.patch("koffee.cli.commands.run")

    cli(first, second)

    configs = [call.kwargs["config"] for call in mock_run.call_args_list]
    assert configs == [embedded_config, asr_config]


def test_cli_explicit_default_overrides_config_file(
    mocker: MockerFixture,
    tmp_path: Path,
) -> None:
    """Tests explicit defaults overriding TOML values."""
    config_file = tmp_path / "custom.toml"
    config_file.write_text('target_language = "fr"\n')
    mock_run = mocker.patch("koffee.cli.commands.run")
    mocker.patch(
        "koffee.cli.embedded.get_subtitle_tracks",
        return_value=[],
    )

    cli(
        korean_video_path,
        config=config_file,
        target_language="en",
    )

    used_config = mock_run.call_args.kwargs["config"]
    assert used_config.target_language == "en"


def test_cli_explicit_true_overrides_false_config_value(
    mocker: MockerFixture,
    tmp_path: Path,
) -> None:
    """Tests explicit true overriding false TOML."""
    config_file = tmp_path / "custom.toml"
    config_file.write_text("vad_filter = false\n")
    mock_run = mocker.patch("koffee.cli.commands.run")
    mocker.patch(
        "koffee.cli.embedded.get_subtitle_tracks",
        return_value=[],
    )

    cli(
        korean_video_path,
        config=config_file,
        vad_filter=True,
    )

    used_config = mock_run.call_args.kwargs["config"]
    assert used_config.vad_filter is True


def test_resolve_paths_glob_includes_subtitles(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Tests subtitle files as glob inputs."""
    monkeypatch.chdir(tmp_path)
    first = tmp_path / "first.srt"
    second = tmp_path / "second.srt"
    first.touch()
    second.touch()

    assert _resolve_paths((Path("*.srt"),)) == [
        first,
        second,
    ]


def test_cli_rejects_output_name_for_multiple_inputs(
    mocker: MockerFixture,
    tmp_path: Path,
) -> None:
    """Tests batch inputs rejecting one output name."""
    first = tmp_path / "first.mp4"
    second = tmp_path / "second.mp4"
    first.touch()
    second.touch()
    mock_run = mocker.patch("koffee.cli.commands.run")

    with pytest.raises(
        IncompatibleOptionsError,
        match="output-name",
    ):
        cli(
            first,
            second,
            output_name="shared",
        )

    mock_run.assert_not_called()
