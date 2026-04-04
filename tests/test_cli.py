"""Tests for CLI."""

import logging
import subprocess
import sys
from pathlib import Path

from pytest_mock import MockerFixture

from koffee.cli import cli

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


def test_overlay_video(mocker: MockerFixture) -> None:
    """Tests that overlay_video flag is passed through to config."""
    mock_translate = mocker.patch("koffee.cli.translate")

    cli(
        korean_video_file_path,
        compute_type="int8",
        output_dir=output_directory_path,
        output_name=output_file_name,
        overlay_video=True,
    )

    mock_translate.assert_called_once()
    config = mock_translate.call_args.kwargs["config"]

    assert config.overlay_video is True


def test_overlay_video_defaults_to_false(mocker: MockerFixture) -> None:
    """Tests that overlay_video defaults to False."""
    mock_translate = mocker.patch("koffee.cli.translate")

    cli(
        korean_video_file_path,
        compute_type="int8",
        output_dir=output_directory_path,
        output_name=output_file_name,
    )

    mock_translate.assert_called_once()
    config = mock_translate.call_args.kwargs["config"]

    assert config.overlay_video is False


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
