"""Tests for CLI."""

import logging
from pathlib import Path

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
