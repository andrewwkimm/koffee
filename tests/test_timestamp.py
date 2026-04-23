"""Tests for timestamp conversion."""

import pytest

from koffee.exceptions import InvalidSubtitleFormatError
from koffee.subtitle import convert_to_timestamp


@pytest.mark.parametrize(
    "subtitle_format",
    [
        ("srt"),
        ("vtt"),
        ("ass"),
    ],
)
def test_convert_to_timestamp(subtitle_format: str) -> None:
    """Tests that float values are formatted to timestamp."""
    timestamps = {
        "srt": {
            10.5: "00:00:10,500",
            60.12: "00:01:00,120",
            3600: "01:00:00,000",
        },
        "vtt": {
            10.5: "00:00:10.500",
            60.12: "00:01:00.120",
            3600: "01:00:00.000",
        },
        "ass": {
            10.5: "0:00:10.50",
            60.12: "0:01:00.12",
            3600: "1:00:00.00",
        },
    }

    for value, expected in timestamps[subtitle_format].items():
        actual = convert_to_timestamp(value, subtitle_format)
        assert actual == expected


@pytest.mark.parametrize("subtitle_format", ["csv", "pdf", "txt", 42, 17.0])
def test_invalid_format(subtitle_format: str) -> None:
    """Tests that the appropriate error is raised when an invalid format is given."""
    error_message = f"Invalid or unsupported subtitle format: {subtitle_format}"
    with pytest.raises(InvalidSubtitleFormatError, match=error_message):
        convert_to_timestamp(42, subtitle_format)
