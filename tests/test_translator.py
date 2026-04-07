"""Tests for Gemini text translation."""

import pytest
from google.genai.errors import APIError, ClientError
from pytest_mock import MockerFixture

from koffee.translator import (
    SYSTEM_PROMPT,
    _attempt_generate,
    _build_prompt,
    _call_with_retries,
    _parse_srt_response,
    _sanitize_response,
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
    """Tests that the prompt includes context section when they are provided."""
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


def test_build_prompt_auto_source_language() -> None:
    """Tests that 'auto' source language omits the source from the prompt."""
    result = _build_prompt(
        chunk=SAMPLE_SEGMENTS,
        context_entries=[],
        source_language="auto",
        target_language="en",
        start_entry=1,
    )

    assert "Translate the following subtitle entries to en." in result
    assert "from" not in result.split("\n")[0]


def test_build_prompt_without_context() -> None:
    """Tests that the prompt omits context section when no context entries are given."""
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
    """Tests that a well-formed SRT response is parsed correctly."""
    result = _parse_srt_response(SAMPLE_SRT_RESPONSE, SAMPLE_SEGMENTS)

    assert len(result) == 2
    assert result[0]["text"] == "Hello."
    assert result[1]["text"] == "How have you been?"


def test_parse_srt_response_preserves_original_timestamps() -> None:
    """Tests that original segment timestamps are preserved."""
    result = _parse_srt_response(SAMPLE_SRT_RESPONSE, SAMPLE_SEGMENTS)

    assert result[0]["start"] == SAMPLE_SEGMENTS[0]["start"]
    assert result[0]["end"] == SAMPLE_SEGMENTS[0]["end"]
    assert result[1]["start"] == SAMPLE_SEGMENTS[1]["start"]
    assert result[1]["end"] == SAMPLE_SEGMENTS[1]["end"]


def test_parse_srt_response_malformed_block_falls_back_to_original() -> None:
    """Tests that a malformed SRT block falls back to the original segment."""
    malformed_block_with_missing_timestamp = "1\nHello."

    result = _parse_srt_response(
        malformed_block_with_missing_timestamp, SAMPLE_SEGMENTS[:1]
    )

    assert result[0] == SAMPLE_SEGMENTS[0]


def test_translate_transcript_single_chunk(mocker: MockerFixture) -> None:
    """Tests translate_transcript with a transcript that fits in one chunk."""
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
    """Tests that translate_transcript sleeps between chunks and stops at last entry."""
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
    """Tests that the API key is passed through to the Gemini client."""
    mock_client_cls = mocker.patch("koffee.translator.genai.Client")
    mock_client_cls.return_value.models.generate_content.return_value.text = (
        "1\n00:00:00,000 --> 00:00:06,360\nHello.\n\n"
        "2\n00:00:07,800 --> 00:00:10,740\nHow have you been?"
    )
    mocker.patch("koffee.translator.time.sleep")

    translate_transcript(SAMPLE_TRANSCRIPT, "en", api_key="test-key")

    mock_client_cls.assert_called_once_with(api_key="test-key")


def test_sanitize_response_strips_markdown_fences() -> None:
    """Tests that markdown code fences are stripped from the response."""
    wrapped = "```srt\n1\n00:00:00,000 --> 00:00:01,000\nHello.\n```"
    result = _sanitize_response(wrapped)
    assert not result.startswith("```")
    assert not result.endswith("```")
    assert "Hello." in result


def test_sanitize_response_normalizes_crlf() -> None:
    """Tests that CRLF line endings are normalized to LF."""
    crlf_text = "1\r\n00:00:00,000 --> 00:00:01,000\r\nHello."
    result = _sanitize_response(crlf_text)
    assert "\r" not in result


def test_sanitize_response_returns_empty_for_none() -> None:
    """Tests that None input returns an empty string."""
    assert _sanitize_response(None) == ""
    assert _sanitize_response("") == ""


def test_parse_srt_response_empty_returns_originals() -> None:
    """Tests that an empty response falls back to original segments."""
    result = _parse_srt_response("", SAMPLE_SEGMENTS)
    assert result == SAMPLE_SEGMENTS


def test_parse_srt_response_none_returns_originals() -> None:
    """Tests that a None response falls back to original segments."""
    result = _parse_srt_response(None, SAMPLE_SEGMENTS)
    assert result == SAMPLE_SEGMENTS


def test_parse_srt_response_extra_blank_lines() -> None:
    """Tests that extra blank lines in the response are filtered out."""
    response_with_extra_blanks = (
        "\n\n1\n00:00:00,000 --> 00:00:06,360\nHello.\n\n\n\n"
        "2\n00:00:07,800 --> 00:00:10,740\nHow have you been?\n\n"
    )
    result = _parse_srt_response(response_with_extra_blanks, SAMPLE_SEGMENTS)
    assert len(result) == 2
    assert result[0]["text"] == "Hello."
    assert result[1]["text"] == "How have you been?"


def test_parse_srt_response_markdown_fenced() -> None:
    """Tests that a markdown-fenced SRT response is parsed correctly."""
    fenced = "```srt\n" + SAMPLE_SRT_RESPONSE + "\n```"
    result = _parse_srt_response(fenced, SAMPLE_SEGMENTS)
    assert len(result) == 2
    assert result[0]["text"] == "Hello."


def test_translate_transcript_reports_progress(mocker: MockerFixture) -> None:
    """Tests that on_progress is called once per chunk with correct ratio."""
    mock_client = mocker.MagicMock()
    mocker.patch("koffee.translator.genai.Client", return_value=mock_client)
    mocker.patch("koffee.translator.time.sleep")
    mocker.patch("koffee.translator.CHUNK_SIZE", 1)

    mock_client.models.generate_content.return_value.text = (
        "1\n00:00:00,000 --> 00:00:06,360\nHello."
    )

    progress_calls = []
    translate_transcript(
        SAMPLE_TRANSCRIPT, "en", api_key=None, on_progress=progress_calls.append
    )

    assert progress_calls == [0.5, 1.0]


def test_call_with_retries_exhaustion(mocker: MockerFixture) -> None:
    """Tests that retry exhaustion raises the last error."""
    mocker.patch("koffee.translator.time.sleep")
    error = APIError(code=500, response_json={"error": "server error"})
    mocker.patch("koffee.translator._attempt_generate", return_value=(None, error))

    with pytest.raises(APIError):
        _call_with_retries(None, "prompt", "model", SYSTEM_PROMPT, max_retries=2)


def test_attempt_generate_non_429_client_error_raises(mocker: MockerFixture) -> None:
    """Tests that non-429 ClientError is raised immediately, not retried."""
    mock_client = mocker.MagicMock()
    mock_client.models.generate_content.side_effect = ClientError(
        code=400, response_json={"error": "bad request"}
    )

    with pytest.raises(ClientError):
        _attempt_generate(mock_client, "prompt", "model", SYSTEM_PROMPT)


def test_attempt_generate_429_returns_error(mocker: MockerFixture) -> None:
    """Tests that 429 ClientError is returned as a retryable error."""
    mock_client = mocker.MagicMock()
    mock_client.models.generate_content.side_effect = ClientError(
        code=429, response_json={"error": "rate limited"}
    )

    result, error = _attempt_generate(mock_client, "prompt", "model", SYSTEM_PROMPT)

    assert result is None
    assert error.code == 429


def test_attempt_generate_api_error_returns_error(mocker: MockerFixture) -> None:
    """Tests that generic APIError is returned as a retryable error."""
    mock_client = mocker.MagicMock()
    mock_client.models.generate_content.side_effect = APIError(
        code=500, response_json={"error": "server error"}
    )

    result, error = _attempt_generate(mock_client, "prompt", "model", SYSTEM_PROMPT)

    assert result is None
    assert error.code == 500


def test_translate_transcript_uses_custom_prompt(mocker: MockerFixture) -> None:
    """Tests that a custom translation prompt is passed to the Gemini API."""
    mock_client = mocker.MagicMock()
    mocker.patch("koffee.translator.genai.Client", return_value=mock_client)
    mocker.patch("koffee.translator.time.sleep")

    mock_client.models.generate_content.return_value.text = (
        "1\n00:00:00,000 --> 00:00:06,360\nHello.\n\n"
        "2\n00:00:07,800 --> 00:00:10,740\nHow have you been?"
    )

    custom_prompt = "You are a medical subtitle translator."
    translate_transcript(
        SAMPLE_TRANSCRIPT, "en", api_key=None, translation_prompt=custom_prompt
    )

    call_kwargs = mock_client.models.generate_content.call_args.kwargs
    assert call_kwargs["config"]["system_instruction"] == custom_prompt


def test_translate_transcript_falls_back_to_default_prompt(
    mocker: MockerFixture,
) -> None:
    """Tests that the default system prompt is used when no custom prompt is given."""
    mock_client = mocker.MagicMock()
    mocker.patch("koffee.translator.genai.Client", return_value=mock_client)
    mocker.patch("koffee.translator.time.sleep")

    mock_client.models.generate_content.return_value.text = (
        "1\n00:00:00,000 --> 00:00:06,360\nHello.\n\n"
        "2\n00:00:07,800 --> 00:00:10,740\nHow have you been?"
    )

    translate_transcript(SAMPLE_TRANSCRIPT, "en", api_key=None)

    call_kwargs = mock_client.models.generate_content.call_args.kwargs
    assert call_kwargs["config"]["system_instruction"] == SYSTEM_PROMPT
