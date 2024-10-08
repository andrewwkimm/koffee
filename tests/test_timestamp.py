"""Tests for timestamp conversion."""

import pytest

from koffee.utils import convert_to_timestamp


@pytest.mark.parametrize(
    "subtitle_format",
    [
        ("srt"),
        ("vtt"),
    ],
)
def test_convert_to_timestamp(subtitle_format: str) -> None:
    """Tests that float values are formatted to timestamp."""
    timestamps = {
        "srt": {
            10.5: "00:00:10,500",
            60.123: "00:01:00,122",
            3600: "01:00:00,000",
        },
        "vtt": {
            10.5: "00:00:10.500",
            60.123: "00:01:00.122",
            3600: "01:00:00.000",
        },
    }

    for value, expected in timestamps[subtitle_format].items():
        actual = convert_to_timestamp(value, subtitle_format)
        assert actual == expected
