"""Tests for Gemini text translation."""

from pytest_mock import MockerFixture

from koffee.translator import (
    _build_prompt,
    _parse_srt_response,
    translate_transcript,
)

SAMPLE_SEGMENTS = [
    {"start": 0.0, "end": 6.36, "text": "안녕하세요."},
    {"start": 7.8, "end": 10.74, "text": "잘 지내셨어요?"},
]

SAMPLE_SRT_RESPONSE = (
    "1\n00:00:00,000 --> 00:00:06,360\nHello.\n\n"
    "2\n00:00:07,800 --> 00:00:10,740\nHow have you been?"
)

SAMPLE_TRANSCRIPT = {
    "segments": SAMPLE_SEGMENTS,
    "language": "ko",
}


def test_build_prompt_with_context() -> None:
    """Test that the prompt includes context section when they are provided."""
    context = [{"start": 0.0, "end": 1.0, "text": "시대를 초월하는 마음."}]

    result = _build_prompt(
        chunk=SAMPLE_SEGMENTS,
        context_entries=context,
        source_language="ko",
        target_language="en",
        start_entry=4,
    )

    assert "[CONTEXT - DO NOT TRANSLATE]" in result
    assert "[TRANSLATE FROM HERE]" in result
    assert "entry 4" in result
    assert "시대를 초월하는 마음." in result
    assert "안녕하세요." in result


def test_build_prompt_without_context() -> None:
    """Test that the prompt omits context section when no context entries are given."""
    result = _build_prompt(
        chunk=SAMPLE_SEGMENTS,
        context_entries=[],
        source_language="ko",
        target_language="en",
        start_entry=1,
    )

    assert "[CONTEXT - DO NOT TRANSLATE]" not in result
    assert "[TRANSLATE FROM HERE]" not in result
    assert "안녕하세요." in result


def test_parse_srt_response() -> None:
    """Test that a well-formed SRT response is parsed correctly."""
    result = _parse_srt_response(SAMPLE_SRT_RESPONSE, SAMPLE_SEGMENTS)

    assert len(result) == 2
    assert result[0]["text"] == "Hello."
    assert result[1]["text"] == "How have you been?"


def test_parse_srt_response_preserves_original_timestamps() -> None:
    """Test that original segment timestamps are preserved."""
    result = _parse_srt_response(SAMPLE_SRT_RESPONSE, SAMPLE_SEGMENTS)

    assert result[0]["start"] == SAMPLE_SEGMENTS[0]["start"]
    assert result[0]["end"] == SAMPLE_SEGMENTS[0]["end"]
    assert result[1]["start"] == SAMPLE_SEGMENTS[1]["start"]
    assert result[1]["end"] == SAMPLE_SEGMENTS[1]["end"]


def test_parse_srt_response_malformed_block_falls_back_to_original() -> None:
    """Test that a malformed SRT block falls back to the original segment."""
    malformed_block_with_missing_timestamp = "1\nHello."

    result = _parse_srt_response(
        malformed_block_with_missing_timestamp, SAMPLE_SEGMENTS[:1]
    )

    assert result[0] == SAMPLE_SEGMENTS[0]


def test_translate_transcript_single_chunk(mocker: MockerFixture) -> None:
    """Test translate_transcript with a transcript that fits in one chunk."""
    mock_client = mocker.MagicMock()
    mocker.patch("koffee.translator.genai.Client", return_value=mock_client)
    mocker.patch("koffee.translator.time.sleep")

    mock_client.models.generate_content.return_value.text = (
        "1\n00:00:00,000 --> 00:00:06,360\nHello.\n\n"
        "2\n00:00:07,800 --> 00:00:10,740\nHow have you been?"
    )

    result = translate_transcript(SAMPLE_TRANSCRIPT, "en", api_key=None)

    assert len(result) == 2
    assert result[0]["text"] == "Hello."
    assert result[1]["text"] == "How have you been?"
    mock_client.models.generate_content.assert_called_once()


def test_translate_transcript_sleeps_between_chunks(mocker: MockerFixture) -> None:
    """Test that translate_transcript sleeps between chunks and stops at last entry."""
    mock_client = mocker.MagicMock()
    mocker.patch("koffee.translator.genai.Client", return_value=mock_client)
    mock_sleep = mocker.patch("koffee.translator.time.sleep")
    mocker.patch("koffee.translator.CHUNK_SIZE", 1)

    mock_client.models.generate_content.return_value.text = (
        "1\n00:00:00,000 --> 00:00:06,360\nHello."
    )

    translate_transcript(SAMPLE_TRANSCRIPT, "en", api_key=None)

    # 2 segments with chunk size 1 = 2 chunks, sleep called once (not after last chunk)
    assert mock_sleep.call_count == 1


def test_translate_transcript_passes_api_key(mocker: MockerFixture) -> None:
    """Test that the API key is passed through to the Gemini client."""
    mock_client_cls = mocker.patch("koffee.translator.genai.Client")
    mock_client_cls.return_value.models.generate_content.return_value.text = (
        "1\n00:00:00,000 --> 00:00:06,360\nHello.\n\n"
        "2\n00:00:07,800 --> 00:00:10,740\nHow have you been?"
    )
    mocker.patch("koffee.translator.time.sleep")

    translate_transcript(SAMPLE_TRANSCRIPT, "en", api_key="test-key")

    mock_client_cls.assert_called_once_with(api_key="test-key")
