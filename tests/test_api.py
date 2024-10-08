"""Tests for the koffee API."""

import pytest

import koffee
from koffee.exceptions import InvalidVideoFileError


def test_invalid_video_file() -> None:
    """Tests that the appropriate error is raised when an invalid file is given."""
    error_message = "Inputted file is not a valid video file or does not exist."
    with pytest.raises(InvalidVideoFileError, match=error_message):
        koffee.translate("invalid_file.mp4")
