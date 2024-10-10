"""Tests for CLI."""

import logging
from pathlib import Path
import subprocess
import sys

import pytest
from pytest_mock import MockerFixture

from koffee.cli import cli


korean_video_file_name = "translated_korean_file"
korean_video_file_path = Path("examples/videos/sample_korean_video.mp4")

japanese_video_file_name = "translated_japanese_file"
japanese_video_file_path = Path("examples/videos/sample_japanese_video.mp4")

output_directory_path = Path("scratch")


@pytest.mark.parametrize(
    "video_file_path, output_name",
    [
        (korean_video_file_path, korean_video_file_name),
        (japanese_video_file_path, japanese_video_file_name),
    ],
)
def test_cli(video_file_path: Path, output_name: str) -> None:
    """Tests CLI processes a valid video file."""
    file_ext = video_file_path.suffix

    cli(
        video_file_path,
        output_dir=output_directory_path,
        output_name=output_name,
    )

    output_video_file_path = output_directory_path / (output_name + file_ext)

    assert output_video_file_path.exists()


def test_script_run() -> None:
    """Tests that the CLI script runs."""
    cli_path = Path("src/koffee/cli.py")
    result = subprocess.run([sys.executable, cli_path], capture_output=True, text=True)

    assert result.returncode == 0


def test_subtitles() -> None:
    """Tests if the subtitles flag writes the subtitle file to disk."""
    subtitle_file_path = Path("subtitles.srt")

    cli(
        korean_video_file_path,
        output_dir=output_directory_path,
        output_name=korean_video_file_name,
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
        output_dir=output_directory_path,
        output_name=korean_video_file_name,
        verbose=True,
    )

    logger_instance.setLevel.assert_called_once_with(logging.DEBUG)
