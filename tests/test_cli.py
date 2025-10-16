"""Tests for CLI."""

import logging
import subprocess
import sys
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from koffee.cli import cli
from koffee.overlay import overlay_subtitles
from koffee.utils import get_video_duration

korean_subtitle_file_path = Path("examples/subtitles/sample_srt_file.srt")
korean_video_file_path = Path("examples/videos/sample_korean_video.mp4")

japanese_subtitle_file_path = Path("examples/subtitles/sample_vtt_file.vtt")
japanese_video_file_path = Path("examples/videos/sample_japanese_video.mp4")

output_directory_path = Path("scratch")
output_file_name = "output_video_file"


@pytest.mark.parametrize(
    "language, subtitle_file_path",
    [
        ("korean", korean_subtitle_file_path),
        ("japanese", japanese_subtitle_file_path),
    ],
)
def test_cli(language: str, subtitle_file_path: Path) -> None:
    """Tests that CLI processes a valid video file."""
    video_file_path = Path("examples/videos") / f"sample_{language}_video.mp4"
    file_ext = video_file_path.suffix

    cli(
        video_file_path,
        compute_type="int8",
        output_dir=output_directory_path,
        output_name=output_file_name,
    )

    translated_video_file_name = f"sample_{language}_video_translated.mp4"
    translated_video_file_path = output_directory_path / translated_video_file_name
    expected_video_file_path = overlay_subtitles(
        subtitle_file_path, video_file_path, translated_video_file_path
    )

    actual_video_file_path = output_directory_path / (output_file_name + file_ext)

    actual = get_video_duration(actual_video_file_path)
    expected = get_video_duration(expected_video_file_path)

    assert actual == expected


def test_script_run() -> None:
    """Tests that the CLI script runs."""
    cli_path = Path("src/koffee/cli.py")
    result = subprocess.run(
        [sys.executable, cli_path], check=False, capture_output=True, text=True
    )

    assert result.returncode == 0


def test_subtitles() -> None:
    """Tests if the subtitles flag writes the subtitle file to disk."""
    subtitle_file_path = Path("subtitles.srt")

    cli(
        korean_video_file_path,
        compute_type="int8",
        output_dir=output_directory_path,
        output_name=output_file_name,
        subtitles=True,
    )

    assert subtitle_file_path.exists()

    subtitle_file_path.unlink()


def test_verbose(mocker: MockerFixture) -> None:
    """Tests if verbose flag sets log level to DEBUG."""
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
