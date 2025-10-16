"""Tests for the koffee API."""

from pathlib import Path

import pytest

import koffee
from koffee.exceptions import InvalidVideoFileError

video_file_path = Path("examples/videos/sample_korean_video.mp4")
output_directory_path = Path("scratch")
output_file_name = "python_output_video_file"


def test_api() -> None:
    """Tests if the API call successfully outputs a file."""
    output_video_file = koffee.translate(
        video_file_path=video_file_path,
        output_dir=output_directory_path,
        output_name=output_file_name,
    )

    output_video_file_path = Path(output_video_file)
    assert output_video_file_path.exists()


def test_invalid_video_file() -> None:
    """Tests that the appropriate error is raised when an invalid file is given."""
    error_message = "Inputted file is not a valid video file or does not exist."
    with pytest.raises(InvalidVideoFileError, match=error_message):
        koffee.translate("invalid_file.mp4")
