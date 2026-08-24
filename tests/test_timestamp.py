"""Tests for timestamp conversion."""

import pytest

from koffee.exceptions import InvalidSubtitleFormatError
from koffee.subtitle import (
    _ass_timestamp_to_seconds,
    _timestamp_to_seconds,
    convert_to_timestamp,
)


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


@pytest.mark.parametrize(
    ("timestamp", "expected_seconds"),
    [
        pytest.param("00:00:07,800", 7.8, id="srt-comma"),
        pytest.param("00:00:07.800", 7.8, id="vtt-dot"),
        pytest.param("01:02:03,004", 3723.004, id="srt-hours"),
        pytest.param("02:03.500", 123.5, id="vtt-no-hours"),
    ],
)
def test_timestamp_to_seconds(timestamp: str, expected_seconds: float) -> None:
    """Tests that SRT and WebVTT timestamps are parsed to seconds."""
    assert _timestamp_to_seconds(timestamp) == expected_seconds


@pytest.mark.parametrize(
    ("timestamp", "expected_seconds"),
    [
        pytest.param("0:00:10.50", 10.5, id="centiseconds"),
        pytest.param("1:02:03.04", 3723.04, id="hours"),
    ],
)
def test_ass_timestamp_to_seconds(timestamp: str, expected_seconds: float) -> None:
    """Tests that ASS timestamps are parsed to seconds."""
    assert _ass_timestamp_to_seconds(timestamp) == expected_seconds


def test_timestamp_to_seconds_rejects_invalid_timestamp() -> None:
    """Tests that a timestamp without minute fields is rejected."""
    with pytest.raises(InvalidSubtitleFormatError, match="Invalid subtitle timestamp"):
        _timestamp_to_seconds("7.800")


@pytest.mark.parametrize("subtitle_format", ["csv", "pdf", "txt"])
def test_invalid_format(subtitle_format: str) -> None:
    """Tests that the appropriate error is raised when an invalid format is given."""
    error_message = f"Invalid or unsupported subtitle format: {subtitle_format}"
    with pytest.raises(InvalidSubtitleFormatError, match=error_message):
        convert_to_timestamp(42, subtitle_format)
