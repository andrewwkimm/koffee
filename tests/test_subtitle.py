"""Tests text to subtitle conversion."""

from pathlib import Path
from typing import Callable, Dict, List

import pytest

from koffee.utils import (
    convert_text_to_srt,
    convert_text_to_vtt,
    convert_to_timestamp,
)


SubtitleConverter = Callable[[List[Dict[str, object]], Path], Path]


@pytest.mark.parametrize(
    "subtitle_format, subtitle_file_name, subtitle_converter",
    [
        ("srt", Path("sample_srt_file.srt"), convert_text_to_srt),
        ("vtt", Path("sample_vtt_file.vtt"), convert_text_to_vtt),
    ],
)
def test_convert_subtitle_conversion(
    subtitle_format: str,
    subtitle_file_name: Path,
    subtitle_converter: SubtitleConverter,
) -> None:
    """Tests that the text is converted to the correct subtitle format."""
    sample_text = [
        {"start": 10.5, "end": 15.0, "text": "Hello, world!"},
        {"start": 20.0, "end": 25.3, "text": "This is a subtitle."},
    ]

    output_dir = Path("examples/subtitles")
    output_path = output_dir / subtitle_file_name

    subtitle_file_path = Path(subtitle_converter(sample_text, output_path))
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
