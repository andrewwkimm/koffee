"""Tests for subtitle conversion."""

from pathlib import Path

import pytest

from koffee.exceptions import InvalidSubtitleFormatError
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
def test_subtitle_generator(
    subtitle_format: str,
    output_dir: Path,
) -> None:
    """Tests that the text is converted to the correct subtitle format."""
    text = [
        {
            "start": 0.0,
            "end": 6.28,
            "text": "When we got out of the long tunnel of the border, it was an eyebled.",
        },
        {
            "start": 7.8,
            "end": 10.74,
            "text": "The bottom of the night has been changed.",
        },
        {
            "start": 12.32,
            "end": 14.94,
            "text": "The train stopped at the signal station.",
        },
        {
            "start": 16.98,
            "end": 24.06,
            "text": "On the other side, a virgin approached and opened a window in front of the Shimmura.",
        },
    ]

    subtitle_file_path = generate_subtitles(subtitle_format, text, output_dir)

    assert subtitle_file_path.exists()

    with open(subtitle_file_path, "r") as f:
        actual = f.read()

    if subtitle_format == "srt":
        expected = """1
00:00:00,000 --> 00:00:06,280
When we got out of the long tunnel of the border, it was an eyebled.

2
00:00:07,800 --> 00:00:10,740
The bottom of the night has been changed.

3
00:00:12,320 --> 00:00:14,940
The train stopped at the signal station.

4
00:00:16,980 --> 00:00:24,060
On the other side, a virgin approached and opened a window in front of the Shimmura.
"""
    elif subtitle_format == "vtt":
        expected = """WEBVTT

00:00:00.000 --> 00:00:06.280
When we got out of the long tunnel of the border, it was an eyebled.

00:00:07.800 --> 00:00:10.740
The bottom of the night has been changed.

00:00:12.320 --> 00:00:14.940
The train stopped at the signal station.

00:00:16.980 --> 00:00:24.060
On the other side, a virgin approached and opened a window in front of the Shimmura.
"""
    else:
        error_message = f"Invalid or unsupported subtitle format: {subtitle_format}"
        raise InvalidSubtitleFormatError(error_message)

    assert actual == expected

    subtitle_file_path.unlink()


@pytest.mark.parametrize("subtitle_format", ["csv", "pdf", "txt"])
def test_invalid_format(subtitle_format: str) -> None:
    """Tests that the appropriate error is raised when an invalid format is given."""
    sample_text = [{"start": 10.5, "end": 15.0, "text": "Hello, world!"}]

    error_message = f"Invalid or unsupported subtitle format: {subtitle_format}"
    with pytest.raises(InvalidSubtitleFormatError, match=error_message):
        generate_subtitles(subtitle_format, sample_text)
