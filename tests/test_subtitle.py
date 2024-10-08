"""Tests for subtitle conversion."""

from pathlib import Path
from typing import Callable, Dict, List

import pytest

from koffee.subtitle import generate_subtitles
from koffee.utils import convert_to_timestamp


SubtitleConverter = Callable[[List[Dict[str, object]], Path], Path]


@pytest.mark.parametrize(
    "subtitle_format, output_dir",
    [
        ("srt", Path("scratch")),
        ("srt", None),
        ("vtt", Path("scratch")),
        ("vtt", None),
    ],
)
def test_convert_subtitle_conversion(
    subtitle_format: str,
    output_dir: Path,
) -> None:
    """Tests that the text is converted to the correct subtitle format."""
    sample_text = [
        {"start": 10.5, "end": 15.0, "text": "Hello, world!"},
        {"start": 20.0, "end": 25.3, "text": "This is a subtitle."},
    ]
    subtitle_file_path = generate_subtitles(subtitle_format, sample_text, output_dir)

    assert subtitle_file_path.exists()

    with open(subtitle_file_path, "r") as f:
        actual = f.read()

    if subtitle_format == "srt":
        expected = """1
00:00:10,500 --> 00:00:15,000
Hello, world!

2
00:00:20,000 --> 00:00:25,300
This is a subtitle.
"""
    elif subtitle_format == "vtt":
        expected = """WEBVTT

00:00:10.500 --> 00:00:15.000
Hello, world!

00:00:20.000 --> 00:00:25.300
This is a subtitle.
"""
    else:
        raise ValueError(f"Unsupported subtitle format: {subtitle_format}")

    assert actual == expected


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
