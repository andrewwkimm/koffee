"""Tests for subtitle conversion."""

from pathlib import Path

import pytest

from koffee.subtitle import generate_subtitles


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

    subtitle_file_path.unlink
