"""Tests for timestamp conversion."""

import pytest

from koffee.exceptions import InvalidSubtitleFormatError
from koffee.subtitle import convert_to_timestamp


@pytest.mark.parametrize(
    ("subtitle_format", "value", "expected"),
    [
        ("srt", 10.5, "00:00:10,500"),
        ("srt", 60.12, "00:01:00,120"),
        ("srt", 3600, "01:00:00,000"),
        ("vtt", 10.5, "00:00:10.500"),
        ("vtt", 60.12, "00:01:00.120"),
        ("vtt", 3600, "01:00:00.000"),
        ("ass", 10.5, "0:00:10.50"),
        ("ass", 60.12, "0:01:00.12"),
        ("ass", 3600, "1:00:00.00"),
    ],
)
def test_convert_to_timestamp(
    subtitle_format: str, value: float, expected: str
) -> None:
    """Tests that float values are formatted to timestamp."""
    assert convert_to_timestamp(value, subtitle_format) == expected


@pytest.mark.parametrize("subtitle_format", ["csv", "pdf", "txt"])
def test_invalid_format(subtitle_format: str) -> None:
    """Tests that the appropriate error is raised when an invalid format is given."""
    error_message = f"Invalid or unsupported subtitle format: {subtitle_format}"
    with pytest.raises(InvalidSubtitleFormatError, match=error_message):
        convert_to_timestamp(42, subtitle_format)
