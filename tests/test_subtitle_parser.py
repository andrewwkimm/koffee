"""Tests for subtitle file parser."""

from koffee.utils.subtitle_parser import parse_subtitle_file

_ASS_EVENT_FMT = (
    "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
)


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


def test_parse_ass_file(tmp_path) -> None:
    """Tests that an ASS file is parsed into segments."""
    ass = tmp_path / "test.ass"
    ass.write_text(
        "[Script Info]\nTitle: Test\nScriptType: v4.00+\n\n"
        "[Events]\n"
        + _ASS_EVENT_FMT
        + "Dialogue: 0,0:00:01.00,0:00:04.50,Default,,0,0,0,,Hello world.\n"
        "Dialogue: 0,0:00:05.00,0:00:08.00,Default,,0,0,0,,Goodbye world.\n",
        encoding="utf-8",
    )

    result = parse_subtitle_file(ass)

    assert len(result) == 2
    assert result[0] == {"start": 1.0, "end": 4.5, "text": "Hello world."}
    assert result[1] == {"start": 5.0, "end": 8.0, "text": "Goodbye world."}


def test_parse_ass_strips_style_tags(tmp_path) -> None:
    """Tests that ASS style override tags are stripped from dialogue text."""
    ass = tmp_path / "test.ass"
    ass.write_text(
        "[Events]\n"
        + _ASS_EVENT_FMT
        + "Dialogue: 0,0:00:01.00,0:00:04.50,Default,,0,0,0,,{\\b1}Bold text{\\b0}\n",
        encoding="utf-8",
    )

    result = parse_subtitle_file(ass)

    assert len(result) == 1
    assert result[0]["text"] == "Bold text"


def test_parse_ass_replaces_newlines(tmp_path) -> None:
    r"""Tests that ASS \\N line breaks are replaced with spaces."""
    ass = tmp_path / "test.ass"
    ass.write_text(
        "[Events]\n"
        + _ASS_EVENT_FMT
        + "Dialogue: 0,0:00:01.00,0:00:04.50,Default,,0,0,0,,Line one\\NLine two\n",
        encoding="utf-8",
    )

    result = parse_subtitle_file(ass)

    assert result[0]["text"] == "Line one Line two"
