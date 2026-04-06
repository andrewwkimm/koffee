"""Tests for CLI."""

import logging
import subprocess
import sys
from pathlib import Path

from pytest_mock import MockerFixture

from koffee.cli import (
    _check_embedded_subtitles,
    _resolve_paths,
    _select_subtitle_track,
    cli,
)
from koffee.data.config import KoffeeConfig

korean_video_file_path = Path("examples/videos/sample_korean_video.mp4")

output_directory_path = Path("scratch")
output_file_name = "cli_output_video_file"


def test_cli(mocker: MockerFixture) -> None:
    """Tests that CLI processes a valid video file."""
    mock_translate = mocker.patch("koffee.cli.translate")

    cli(
        korean_video_file_path,
        compute_type="int8",
        output_dir=output_directory_path,
        output_name=output_file_name,
    )

    mock_translate.assert_called_once()
    config = mock_translate.call_args.kwargs["config"]

    assert config.compute_type == "int8"
    assert config.output_dir == output_directory_path
    assert config.output_name == output_file_name


def test_script_run() -> None:
    """Tests that the CLI script runs."""
    cli_path = Path("src/koffee/cli.py")
    result = subprocess.run(
        [sys.executable, cli_path], check=False, capture_output=True, text=True
    )

    assert result.returncode == 0


def test_overlay_soft(mocker: MockerFixture) -> None:
    """Tests that overlay flag is passed through to config."""
    mock_translate = mocker.patch("koffee.cli.translate")

    cli(
        korean_video_file_path,
        compute_type="int8",
        output_dir=output_directory_path,
        output_name=output_file_name,
        overlay="soft",
    )

    mock_translate.assert_called_once()
    config = mock_translate.call_args.kwargs["config"]

    assert config.overlay == "soft"


def test_overlay_defaults_to_none(mocker: MockerFixture) -> None:
    """Tests that overlay defaults to none."""
    mock_translate = mocker.patch("koffee.cli.translate")

    cli(
        korean_video_file_path,
        compute_type="int8",
        output_dir=output_directory_path,
        output_name=output_file_name,
    )

    mock_translate.assert_called_once()
    config = mock_translate.call_args.kwargs["config"]

    assert config.overlay == "none"


def test_verbose(mocker: MockerFixture) -> None:
    """Tests if verbose flag sets log level to DEBUG."""
    mocker.patch("koffee.cli.translate")
    mock_logger = mocker.patch("logging.getLogger")
    logger_instance = mock_logger.return_value

    cli(
        korean_video_file_path,
        compute_type="int8",
        output_dir=output_directory_path,
        output_name=output_file_name,
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
    mock_translate = mocker.patch("koffee.cli.translate")
    mocker.patch("koffee.cli.get_subtitle_tracks", return_value=[])

    cli(
        korean_video_file_path,
        output_dir=output_directory_path,
        dry_run=True,
    )

    mock_translate.assert_not_called()


def test_dry_run_subtitle_file(mocker: MockerFixture, tmp_path) -> None:
    """Tests that dry-run shows subtitle translation mode for .srt files."""
    mock_translate = mocker.patch("koffee.cli.translate")
    mocker.patch("koffee.cli.get_subtitle_tracks", return_value=[])
    srt = tmp_path / "test.srt"
    srt.touch()

    cli(srt, dry_run=True)

    mock_translate.assert_not_called()


def test_dry_run_with_overlay(mocker: MockerFixture) -> None:
    """Tests that dry-run shows overlay info when flag is set."""
    mocker.patch("koffee.cli.translate")
    mocker.patch("koffee.cli.get_subtitle_tracks", return_value=[])

    cli(
        korean_video_file_path,
        output_dir=output_directory_path,
        dry_run=True,
        overlay="soft",
    )


def test_check_embedded_subtitles_skips_subtitle_files(
    tmp_path,
) -> None:
    """Tests that subtitle files skip the embedded subtitle check."""
    srt = tmp_path / "test.srt"
    srt.touch()
    config = KoffeeConfig()

    result = _check_embedded_subtitles(srt, config)

    assert result.use_embedded_subtitles is False


def test_check_embedded_subtitles_no_tracks(
    mocker: MockerFixture,
) -> None:
    """Tests that videos with no subtitle tracks return config unchanged."""
    mocker.patch("koffee.cli.get_subtitle_tracks", return_value=[])
    config = KoffeeConfig()

    result = _check_embedded_subtitles(korean_video_file_path, config)

    assert result.use_embedded_subtitles is False


def test_check_embedded_subtitles_user_accepts(
    mocker: MockerFixture,
) -> None:
    """Tests that accepting embedded subtitles updates config."""
    tracks = [{"index": 0, "codec": "srt", "tags": {"language": "ko"}}]
    mocker.patch("koffee.cli.get_subtitle_tracks", return_value=tracks)
    mocker.patch("builtins.input", return_value="y")
    config = KoffeeConfig()

    result = _check_embedded_subtitles(korean_video_file_path, config)

    assert result.use_embedded_subtitles is True
    assert result.source_language == "ko"


def test_check_embedded_subtitles_user_declines(
    mocker: MockerFixture,
) -> None:
    """Tests that declining embedded subtitles keeps config unchanged."""
    mocker.patch(
        "koffee.cli.get_subtitle_tracks",
        return_value=[{"index": 0, "codec": "srt"}],
    )
    mocker.patch("builtins.input", return_value="n")
    config = KoffeeConfig()

    result = _check_embedded_subtitles(korean_video_file_path, config)

    assert result.use_embedded_subtitles is False


def test_translate_with_progress_subtitle_file(mocker: MockerFixture, tmp_path) -> None:
    """Tests that subtitle files skip the ASR progress bar."""
    mock_translate = mocker.patch("koffee.cli.translate")
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
    mock_translate = mocker.patch("koffee.cli.translate")
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
    tracks = [{"index": 0, "tags": {}}]

    index, lang = _select_subtitle_track(tracks)

    assert index == 0
    assert lang is None
