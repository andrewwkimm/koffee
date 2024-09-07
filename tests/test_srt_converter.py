"""Tests text to SRT conversion."""

from pathlib import Path

from koffee.utils.text_to_srt_converter import convert_text_to_srt, convert_to_timestamp


def test_convert_text_to_srt() -> None:
    """Tests that the text is converted to SRT."""
    sample_text = [
        {"start": 10.5, "end": 15.0, "text": "Hello, world!"},
        {"start": 20.0, "end": 25.3, "text": "This is a subtitle."},
    ]

    output_path = Path("examples/subtitles/sample_srt_file.srt")

    srt_file_path = Path(convert_text_to_srt(sample_text, output_path))
    assert srt_file_path.exists()

    with open(srt_file_path, "r") as f:
        actual = f.read()

    expected = """1
00:00:10,500 --> 00:00:15,000
Hello, world!

2
00:00:20,000 --> 00:00:25,300
This is a subtitle.
"""

    assert actual == expected


def test_convert_to_timestamp() -> None:
    """Tests that float values are formatted to timestamp."""
    test_cases = {
        10.5: "00:00:10,500",
        60.123: "00:01:00,122",
        3600: "01:00:00,000",
    }

    for value, expected in test_cases.items():
        assert convert_to_timestamp(value) == expected
