"""Tests for subtitle file parser."""

from koffee.utils.subtitle_parser import parse_subtitle_file


def test_parse_srt_file(tmp_path) -> None:
    """Tests that an SRT file is parsed into segments."""
    srt = tmp_path / "test.srt"
    srt.write_text(
        "1\n00:00:01,000 --> 00:00:04,500\nHello world.\n\n"
        "2\n00:00:05,000 --> 00:00:08,000\nGoodbye world.\n",
        encoding="utf-8",
    )

    result = parse_subtitle_file(srt)

    assert len(result) == 2
    assert result[0] == {"start": 1.0, "end": 4.5, "text": "Hello world."}
    assert result[1] == {"start": 5.0, "end": 8.0, "text": "Goodbye world."}


def test_parse_vtt_file(tmp_path) -> None:
    """Tests that a VTT file is parsed into segments."""
    vtt = tmp_path / "test.vtt"
    vtt.write_text(
        "WEBVTT\n\n"
        "00:00:01.000 --> 00:00:04.500\nHello world.\n\n"
        "00:00:05.000 --> 00:00:08.000\nGoodbye world.\n",
        encoding="utf-8",
    )

    result = parse_subtitle_file(vtt)

    assert len(result) == 2
    assert result[0]["start"] == 1.0
    assert result[1]["text"] == "Goodbye world."


def test_parse_multiline_text(tmp_path) -> None:
    """Tests that multi-line subtitle text is joined."""
    srt = tmp_path / "test.srt"
    srt.write_text(
        "1\n00:00:01,000 --> 00:00:04,500\nLine one\nLine two\n",
        encoding="utf-8",
    )

    result = parse_subtitle_file(srt)

    assert result[0]["text"] == "Line one Line two"


def test_parse_empty_file(tmp_path) -> None:
    """Tests that an empty file returns no segments."""
    srt = tmp_path / "test.srt"
    srt.write_text("", encoding="utf-8")

    result = parse_subtitle_file(srt)

    assert result == []
