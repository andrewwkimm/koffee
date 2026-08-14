"""Tests for text translation."""

import pytest
from google.genai.errors import APIError, ClientError
from pytest_mock import MockerFixture

from koffee.exceptions import TranslationIntegrityError
from koffee.llm import anthropic, google, ollama, openai
from koffee.schemas.domain import Segment, Transcript
from koffee.translator import (
    SYSTEM_PROMPT,
    _build_prompt,
    _chunk_segments,
    _load_backend,
    _parse_srt_response,
    _sanitize_response,
    translate,
)

SAMPLE_SEGMENTS: list[Segment] = [
    Segment(start=0.0, end=6.36, text="안녕하세요."),
    Segment(start=7.8, end=10.74, text="잘 지내셨어요?"),
]

SAMPLE_SRT_RESPONSE = (
    "1\n00:00:00,000 --> 00:00:06,360\nHello.\n\n"
    "2\n00:00:07,800 --> 00:00:10,740\nHow have you been?"
)

SAMPLE_TRANSCRIPT: Transcript = Transcript(segments=SAMPLE_SEGMENTS, language="ko")


def _configure_gemini_chunk_responses(
    mocker: MockerFixture,
    mock_client,
) -> None:
    """Configures valid global-ID responses for the two sample chunks."""
    mock_client.models.generate_content.side_effect = [
        mocker.MagicMock(text="1\n00:00:00,000 --> 00:00:06,360\nHello."),
        mocker.MagicMock(text="2\n00:00:07,800 --> 00:00:10,740\nHow have you been?"),
    ]


def _configure_ollama_chunk_responses(
    mocker: MockerFixture,
    mock_client,
) -> None:
    """Configures valid global-ID responses for the two sample chunks."""
    responses = []
    for text in (
        "1\n00:00:00,000 --> 00:00:06,360\nHello.",
        "2\n00:00:07,800 --> 00:00:10,740\nHow have you been?",
    ):
        response = mocker.MagicMock()
        response.choices = [mocker.MagicMock(message=mocker.MagicMock(content=text))]
        responses.append(response)
    mock_client.chat.completions.create.side_effect = responses


def test_build_prompt_with_context() -> None:
    """Tests that the prompt includes context section when they are provided."""
    context: list[Segment] = [Segment(start=0.0, end=1.0, text="시대를 초월하는 마음.")]

    result = _build_prompt(
        chunk=SAMPLE_SEGMENTS,
        context_segments=context,
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
        context_segments=[],
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
        context_segments=[],
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

    assert len(result) == len(SAMPLE_SEGMENTS)
    assert result[0].text == "Hello."
    assert result[1].text == "How have you been?"


def test_parse_srt_response_preserves_original_timestamps() -> None:
    """Tests that original segment timestamps are preserved."""
    result = _parse_srt_response(SAMPLE_SRT_RESPONSE, SAMPLE_SEGMENTS)

    assert result[0].start == SAMPLE_SEGMENTS[0].start
    assert result[0].end == SAMPLE_SEGMENTS[0].end
    assert result[1].start == SAMPLE_SEGMENTS[1].start
    assert result[1].end == SAMPLE_SEGMENTS[1].end


def test_parse_srt_response_rejects_malformed_block() -> None:
    """Tests that a malformed SRT block fails integrity validation."""
    malformed_block_with_missing_timestamp = "1\nHello."

    with pytest.raises(TranslationIntegrityError, match="invalid timestamp"):
        _parse_srt_response(
            malformed_block_with_missing_timestamp,
            SAMPLE_SEGMENTS[:1],
        )


def test_build_prompt_uses_global_entry_ids() -> None:
    """Tests that chunk prompts retain global entry IDs and output rules."""
    result = _build_prompt(
        chunk=SAMPLE_SEGMENTS,
        context_segments=[],
        source_language="ko",
        target_language="en",
        start_entry=4,
    )

    assert "Use every entry ID from 4 through 5 exactly once" in result
    assert "\n4\n" in result
    assert "\n5\n" in result


def test_parse_srt_response_accepts_global_entry_ids() -> None:
    """Tests that global response IDs map onto the current chunk."""
    response = (
        "4\n00:00:00,000 --> 00:00:06,360\nHello.\n\n"
        "5\n00:00:07,800 --> 00:00:10,740\nHow have you been?"
    )

    result = _parse_srt_response(response, SAMPLE_SEGMENTS, start_entry=4)

    assert [segment.text for segment in result] == [
        "Hello.",
        "How have you been?",
    ]


def test_parse_srt_response_rejects_duplicate_entry_id() -> None:
    """Tests that duplicate response IDs fail integrity validation."""
    response = (
        "1\n00:00:00,000 --> 00:00:06,360\nHello.\n\n"
        "1\n00:00:07,800 --> 00:00:10,740\nHow have you been?"
    )

    with pytest.raises(TranslationIntegrityError, match="duplicate entry ID 1"):
        _parse_srt_response(response, SAMPLE_SEGMENTS)


def test_parse_srt_response_rejects_empty_translated_text() -> None:
    """Tests that an entry without translated text fails validation."""
    response = "1\n00:00:00,000 --> 00:00:06,360\n"

    with pytest.raises(TranslationIntegrityError, match="no translated text"):
        _parse_srt_response(response, SAMPLE_SEGMENTS[:1])


def test_parse_srt_response_rejects_missing_entry_id() -> None:
    """Tests that an incomplete translation response fails validation."""
    response = "1\n00:00:00,000 --> 00:00:06,360\nHello."

    with pytest.raises(TranslationIntegrityError, match=r"missing entry IDs \[2\]"):
        _parse_srt_response(response, SAMPLE_SEGMENTS)


def test_parse_srt_response_rejects_unexpected_entry_id() -> None:
    """Tests that an out-of-range response ID fails validation."""
    response = (
        "1\n00:00:00,000 --> 00:00:06,360\nHello.\n\n"
        "3\n00:00:07,800 --> 00:00:10,740\nHow have you been?"
    )

    with pytest.raises(
        TranslationIntegrityError,
        match=r"unexpected entry IDs \[3\]",
    ):
        _parse_srt_response(response, SAMPLE_SEGMENTS)


def test_translate_single_chunk(mocker: MockerFixture) -> None:
    """Tests translate with a transcript that fits in one chunk."""
    mock_client = mocker.MagicMock()
    mocker.patch.object(google, "create_client", return_value=mock_client)
    mocker.patch("koffee.translator.time.sleep")

    mock_client.models.generate_content.return_value.text = (
        "1\n00:00:00,000 --> 00:00:06,360\nHello.\n\n"
        "2\n00:00:07,800 --> 00:00:10,740\nHow have you been?"
    )

    result = translate(SAMPLE_TRANSCRIPT, "en", api_key=None, translator="google")

    assert len(result) == len(SAMPLE_SEGMENTS)
    assert result[0].text == "Hello."
    assert result[1].text == "How have you been?"
    mock_client.models.generate_content.assert_called_once()


def test_translate_sleeps_between_chunks(mocker: MockerFixture) -> None:
    """Tests that translate sleeps between chunks and stops at last entry."""
    mock_client = mocker.MagicMock()
    mocker.patch.object(google, "create_client", return_value=mock_client)
    mock_sleep = mocker.patch("koffee.translator.time.sleep")
    mocker.patch("koffee.translator.CHUNK_SIZE", 1)

    _configure_gemini_chunk_responses(mocker, mock_client)

    translate(SAMPLE_TRANSCRIPT, "en", api_key=None, translator="google")

    # 2 segments with chunk size 1 = 2 chunks, sleep called once (not after last chunk)
    expected_sleep_seconds = 4
    assert mock_sleep.call_count == 1
    assert mock_sleep.call_args.args[0] == expected_sleep_seconds


def test_translate_skips_sleep_when_zero(mocker: MockerFixture) -> None:
    """Tests that sleep_requests=0 skips time.sleep between chunks entirely."""
    mock_client = mocker.MagicMock()
    mocker.patch.object(google, "create_client", return_value=mock_client)
    mock_sleep = mocker.patch("koffee.translator.time.sleep")
    mocker.patch("koffee.translator.CHUNK_SIZE", 1)
    _configure_gemini_chunk_responses(mocker, mock_client)

    translate(
        SAMPLE_TRANSCRIPT, "en", api_key=None, translator="google", sleep_seconds=0
    )

    assert mock_sleep.call_count == 0


def test_translate_ollama_defaults_to_no_sleep(
    mocker: MockerFixture,
) -> None:
    """Tests that the Ollama provider uses zero sleep by default."""
    mock_client = mocker.MagicMock()
    mocker.patch("koffee.llm.ollama.create_client", return_value=mock_client)
    mock_sleep = mocker.patch("koffee.translator.time.sleep")

    response = mocker.MagicMock()
    response.choices = [mocker.MagicMock()]
    response.choices[0].message.content = (
        "1\n00:00:00,000 --> 00:00:06,360\nHello.\n\n"
        "2\n00:00:07,800 --> 00:00:10,740\nHow have you been?"
    )
    mock_client.chat.completions.create.return_value = response

    translate(SAMPLE_TRANSCRIPT, "en", api_key=None, translator="ollama")

    mock_sleep.assert_not_called()


def test_translate_explicit_sleep_overrides_default(mocker: MockerFixture) -> None:
    """Tests that an explicit sleep_requests value overrides the provider default."""
    mock_client = mocker.MagicMock()
    mocker.patch.object(google, "create_client", return_value=mock_client)
    mock_sleep = mocker.patch("koffee.translator.time.sleep")
    mocker.patch("koffee.translator.CHUNK_SIZE", 1)
    _configure_gemini_chunk_responses(mocker, mock_client)

    sleep_seconds = 9
    translate(
        SAMPLE_TRANSCRIPT,
        "en",
        api_key=None,
        translator="google",
        sleep_seconds=sleep_seconds,
    )

    assert mock_sleep.call_args.args[0] == sleep_seconds


def test_translate_passes_api_key(mocker: MockerFixture) -> None:
    """Tests that the API key is passed through to the backend client."""
    mock_create = mocker.patch.object(google, "create_client")
    mock_create.return_value.models.generate_content.return_value.text = (
        "1\n00:00:00,000 --> 00:00:06,360\nHello.\n\n"
        "2\n00:00:07,800 --> 00:00:10,740\nHow have you been?"
    )
    mocker.patch("koffee.translator.time.sleep")

    translate(SAMPLE_TRANSCRIPT, "en", api_key="test-key", translator="google")

    mock_create.assert_called_once_with("test-key")


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


def test_sanitize_response_strips_think_block() -> None:
    """Tests that Qwen3-style <think>...</think> blocks are stripped."""
    with_think = (
        "<think>\nsome reasoning\n</think>\n1\n00:00:00,000 --> 00:00:01,000\nHello."
    )
    result = _sanitize_response(with_think)
    assert "<think>" not in result
    assert "some reasoning" not in result
    assert "Hello." in result


def test_sanitize_response_strips_unclosed_think_block() -> None:
    """Tests that an unclosed <think> block is stripped from the opening tag onward."""
    with_unclosed = "<think>\nsome reasoning\n1\n00:00:00,000 --> 00:00:01,000\nHello."
    result = _sanitize_response(with_unclosed)
    assert "<think>" not in result


def test_parse_srt_response_rejects_empty_response() -> None:
    """Tests that an empty provider response fails integrity validation."""
    with pytest.raises(TranslationIntegrityError, match="empty response"):
        _parse_srt_response("", SAMPLE_SEGMENTS)


def test_parse_srt_response_rejects_none_response() -> None:
    """Tests that a missing provider response fails integrity validation."""
    with pytest.raises(TranslationIntegrityError, match="empty response"):
        _parse_srt_response(None, SAMPLE_SEGMENTS)


def test_parse_srt_response_extra_blank_lines() -> None:
    """Tests that extra blank lines in the response are filtered out."""
    response_with_extra_blanks = (
        "\n\n1\n00:00:00,000 --> 00:00:06,360\nHello.\n\n\n\n"
        "2\n00:00:07,800 --> 00:00:10,740\nHow have you been?\n\n"
    )
    result = _parse_srt_response(response_with_extra_blanks, SAMPLE_SEGMENTS)
    assert len(result) == len(SAMPLE_SEGMENTS)
    assert result[0].text == "Hello."
    assert result[1].text == "How have you been?"


def test_parse_srt_response_markdown_fenced() -> None:
    """Tests that a markdown-fenced SRT response is parsed correctly."""
    fenced = "```srt\n" + SAMPLE_SRT_RESPONSE + "\n```"
    result = _parse_srt_response(fenced, SAMPLE_SEGMENTS)
    assert len(result) == len(SAMPLE_SEGMENTS)
    assert result[0].text == "Hello."


def test_translate_reports_progress(mocker: MockerFixture) -> None:
    """Tests that on_progress is called once per chunk with correct ratio."""
    mock_client = mocker.MagicMock()
    mocker.patch.object(google, "create_client", return_value=mock_client)
    mocker.patch("koffee.translator.time.sleep")
    mocker.patch("koffee.translator.CHUNK_SIZE", 1)

    _configure_gemini_chunk_responses(mocker, mock_client)

    progress_calls = []
    translate(
        SAMPLE_TRANSCRIPT,
        "en",
        api_key=None,
        on_progress=progress_calls.append,
        translator="google",
    )

    assert progress_calls == [0.5, 1.0]


def test_gemini_attempt_generate_raises_on_error(mocker: MockerFixture) -> None:
    """Tests that errors from the Gemini client propagate out."""
    mock_client = mocker.MagicMock()
    mock_client.models.generate_content.side_effect = ClientError(
        code=400, response_json={"error": "bad request"}
    )

    with pytest.raises(ClientError):
        google.attempt_generate(mock_client, "prompt", "model", SYSTEM_PROMPT)


def test_gemini_is_retryable_429() -> None:
    """Tests that a 429 ClientError is classified as retryable."""
    exc = ClientError(code=429, response_json={"error": "rate limited"})
    assert google.is_retryable(exc) is True


def test_gemini_is_retryable_non_429_client_error() -> None:
    """Tests that a non-429 ClientError is classified as non-retryable."""
    exc = ClientError(code=400, response_json={"error": "bad request"})
    assert google.is_retryable(exc) is False


def test_gemini_is_retryable_api_error() -> None:
    """Tests that a generic APIError is classified as retryable."""
    exc = APIError(code=500, response_json={"error": "server error"})
    assert google.is_retryable(exc) is True


def test_gemini_is_retryable_unrelated_exception() -> None:
    """Tests that an unrelated exception is classified as non-retryable."""
    assert google.is_retryable(ValueError("nope")) is False


def test_translate_uses_custom_prompt(mocker: MockerFixture) -> None:
    """Tests that a custom translation prompt is passed to the LLM backend."""
    mock_client = mocker.MagicMock()
    mocker.patch.object(google, "create_client", return_value=mock_client)
    mocker.patch("koffee.translator.time.sleep")

    mock_client.models.generate_content.return_value.text = (
        "1\n00:00:00,000 --> 00:00:06,360\nHello.\n\n"
        "2\n00:00:07,800 --> 00:00:10,740\nHow have you been?"
    )

    custom_prompt = "You are a medical subtitle translator."
    translate(
        SAMPLE_TRANSCRIPT,
        "en",
        api_key=None,
        prompt=custom_prompt,
        translator="google",
    )

    call_kwargs = mock_client.models.generate_content.call_args.kwargs
    assert call_kwargs["config"]["system_instruction"] == custom_prompt
    assert "Use every entry ID from 1 through 2 exactly once" in call_kwargs["contents"]


def test_translate_falls_back_to_default_prompt(
    mocker: MockerFixture,
) -> None:
    """Tests that the default system prompt is used when no custom prompt is given."""
    mock_client = mocker.MagicMock()
    mocker.patch.object(google, "create_client", return_value=mock_client)
    mocker.patch("koffee.translator.time.sleep")

    mock_client.models.generate_content.return_value.text = (
        "1\n00:00:00,000 --> 00:00:06,360\nHello.\n\n"
        "2\n00:00:07,800 --> 00:00:10,740\nHow have you been?"
    )

    translate(SAMPLE_TRANSCRIPT, "en", api_key=None, translator="google")

    call_kwargs = mock_client.models.generate_content.call_args.kwargs
    assert call_kwargs["config"]["system_instruction"] == SYSTEM_PROMPT


def test_load_backend_unknown_raises() -> None:
    """Tests that an unknown backend name raises ValueError."""
    with pytest.raises(ValueError, match="Unknown translation backend"):
        _load_backend("unknown")


def test_load_backend_gemini() -> None:
    """Tests that the Gemini provider object is registered."""
    backend = _load_backend("google")

    assert backend is google.TRANSLATOR
    assert backend.name == "google"
    assert backend.default_model == google.DEFAULT_MODEL


def test_gemini_extract_text() -> None:
    """Tests that text is extracted from a Gemini response."""
    from unittest.mock import MagicMock  # noqa: PLC0415

    response = MagicMock()
    response.text = "Hello."
    assert google.extract_text(response) == "Hello."


def test_chatgpt_extract_text() -> None:
    """Tests that text is extracted from a ChatGPT response."""
    from unittest.mock import MagicMock  # noqa: PLC0415

    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.content = "Hello."
    assert openai.extract_text(response) == "Hello."


def test_claude_extract_text() -> None:
    """Tests that text is extracted from a Claude response."""
    from unittest.mock import MagicMock  # noqa: PLC0415

    response = MagicMock()
    response.content = [MagicMock()]
    response.content[0].text = "Hello."
    assert anthropic.extract_text(response) == "Hello."


def test_translate_uses_default_model(mocker: MockerFixture) -> None:
    """Tests that the default model is used when none is specified."""
    mock_client = mocker.MagicMock()
    mocker.patch.object(google, "create_client", return_value=mock_client)
    mocker.patch("koffee.translator.time.sleep")

    mock_client.models.generate_content.return_value.text = (
        "1\n00:00:00,000 --> 00:00:06,360\nHello.\n\n"
        "2\n00:00:07,800 --> 00:00:10,740\nHow have you been?"
    )

    translate(SAMPLE_TRANSCRIPT, "en", api_key=None, translator="google")

    call_kwargs = mock_client.models.generate_content.call_args.kwargs
    assert call_kwargs["model"] == "gemini-2.5-flash"


# --- ChatGPT backend tests ---


def test_chatgpt_attempt_generate_success(mocker: MockerFixture) -> None:
    """Tests that a successful ChatGPT call returns the response."""
    mock_client = mocker.MagicMock()
    mock_response = mocker.MagicMock()
    mock_client.chat.completions.create.return_value = mock_response

    result = openai.attempt_generate(mock_client, "prompt", "gpt-4o", SYSTEM_PROMPT)

    assert result is mock_response


def test_chatgpt_attempt_generate_raises_on_error(mocker: MockerFixture) -> None:
    """Tests that errors from the OpenAI client propagate out."""
    from openai import APIStatusError  # noqa: PLC0415

    mock_client = mocker.MagicMock()
    mock_response = mocker.MagicMock()
    mock_response.status_code = 400
    mock_response.headers = {}
    mock_response.json.return_value = {"error": {"message": "bad request"}}
    exc = APIStatusError(message="bad request", response=mock_response, body=None)
    mock_client.chat.completions.create.side_effect = exc

    with pytest.raises(APIStatusError):
        openai.attempt_generate(mock_client, "prompt", "gpt-4o", SYSTEM_PROMPT)


def test_chatgpt_is_retryable_rate_limit(mocker: MockerFixture) -> None:
    """Tests that a RateLimitError is classified as retryable."""
    from openai import RateLimitError as OpenAIRateLimitError  # noqa: PLC0415

    mock_response = mocker.MagicMock()
    mock_response.status_code = 429
    mock_response.headers = {}
    mock_response.json.return_value = {"error": {"message": "rate limited"}}
    exc = OpenAIRateLimitError(
        message="rate limited", response=mock_response, body=None
    )
    assert openai.is_retryable(exc) is True


def test_chatgpt_is_retryable_connection_error(mocker: MockerFixture) -> None:
    """Tests that a connection error is classified as retryable."""
    from openai import APIConnectionError as OpenAIConnectionError  # noqa: PLC0415

    exc = OpenAIConnectionError(request=mocker.MagicMock())
    assert openai.is_retryable(exc) is True


def test_chatgpt_is_retryable_5xx(mocker: MockerFixture) -> None:
    """Tests that a 5xx APIStatusError is classified as retryable."""
    from openai import APIStatusError  # noqa: PLC0415

    mock_response = mocker.MagicMock()
    mock_response.status_code = 503
    mock_response.headers = {}
    mock_response.json.return_value = {"error": {"message": "unavailable"}}
    exc = APIStatusError(message="unavailable", response=mock_response, body=None)
    assert openai.is_retryable(exc) is True


def test_chatgpt_is_retryable_4xx_not_retryable(mocker: MockerFixture) -> None:
    """Tests that a non-429 4xx APIStatusError is classified as non-retryable."""
    from openai import APIStatusError  # noqa: PLC0415

    mock_response = mocker.MagicMock()
    mock_response.status_code = 400
    mock_response.headers = {}
    mock_response.json.return_value = {"error": {"message": "bad request"}}
    exc = APIStatusError(message="bad request", response=mock_response, body=None)
    assert openai.is_retryable(exc) is False


def test_chatgpt_translate(mocker: MockerFixture) -> None:
    """Tests that translate works with the chatgpt backend."""
    mock_client = mocker.MagicMock()
    mocker.patch.object(openai, "create_client", return_value=mock_client)
    mocker.patch("koffee.translator.time.sleep")

    mock_response = mocker.MagicMock()
    mock_response.choices = [mocker.MagicMock()]
    mock_response.choices[0].message.content = (
        "1\n00:00:00,000 --> 00:00:06,360\nHello.\n\n"
        "2\n00:00:07,800 --> 00:00:10,740\nHow have you been?"
    )
    mock_client.chat.completions.create.return_value = mock_response

    result = translate(SAMPLE_TRANSCRIPT, "en", api_key="test-key", translator="openai")

    assert len(result) == len(SAMPLE_SEGMENTS)
    assert result[0].text == "Hello."
    assert result[1].text == "How have you been?"


# --- Claude backend tests ---


def test_claude_attempt_generate_success(mocker: MockerFixture) -> None:
    """Tests that a successful Claude call returns the response."""
    mock_client = mocker.MagicMock()
    mock_response = mocker.MagicMock()
    mock_client.messages.create.return_value = mock_response

    result = anthropic.attempt_generate(
        mock_client, "prompt", "claude-sonnet-4-20250514", SYSTEM_PROMPT
    )

    assert result is mock_response


def test_claude_attempt_generate_raises_on_error(mocker: MockerFixture) -> None:
    """Tests that errors from the Anthropic client propagate out."""
    from anthropic import APIStatusError  # noqa: PLC0415

    mock_client = mocker.MagicMock()
    mock_response = mocker.MagicMock()
    mock_response.status_code = 400
    mock_response.headers = {}
    mock_response.json.return_value = {"error": {"message": "bad request"}}
    exc = APIStatusError(message="bad request", response=mock_response, body=None)
    mock_client.messages.create.side_effect = exc

    with pytest.raises(APIStatusError):
        anthropic.attempt_generate(
            mock_client, "prompt", "claude-sonnet-4-20250514", SYSTEM_PROMPT
        )


def test_claude_is_retryable_rate_limit(mocker: MockerFixture) -> None:
    """Tests that a RateLimitError is classified as retryable."""
    from anthropic import RateLimitError as AnthropicRateLimitError  # noqa: PLC0415

    mock_response = mocker.MagicMock()
    mock_response.status_code = 429
    mock_response.headers = {}
    mock_response.json.return_value = {"error": {"message": "rate limited"}}
    exc = AnthropicRateLimitError(
        message="rate limited", response=mock_response, body=None
    )
    assert anthropic.is_retryable(exc) is True


def test_claude_is_retryable_connection_error(mocker: MockerFixture) -> None:
    """Tests that a connection error is classified as retryable."""
    from anthropic import (  # noqa: PLC0415
        APIConnectionError as AnthropicConnectionError,
    )

    exc = AnthropicConnectionError(request=mocker.MagicMock())
    assert anthropic.is_retryable(exc) is True


def test_claude_is_retryable_5xx(mocker: MockerFixture) -> None:
    """Tests that a 5xx APIStatusError is classified as retryable."""
    from anthropic import APIStatusError  # noqa: PLC0415

    mock_response = mocker.MagicMock()
    mock_response.status_code = 503
    mock_response.headers = {}
    mock_response.json.return_value = {"error": {"message": "unavailable"}}
    exc = APIStatusError(message="unavailable", response=mock_response, body=None)
    assert anthropic.is_retryable(exc) is True


def test_claude_is_retryable_4xx_not_retryable(mocker: MockerFixture) -> None:
    """Tests that a non-429 4xx APIStatusError is classified as non-retryable."""
    from anthropic import APIStatusError  # noqa: PLC0415

    mock_response = mocker.MagicMock()
    mock_response.status_code = 400
    mock_response.headers = {}
    mock_response.json.return_value = {"error": {"message": "bad request"}}
    exc = APIStatusError(message="bad request", response=mock_response, body=None)
    assert anthropic.is_retryable(exc) is False


def test_load_backend_ollama() -> None:
    """Tests that the ollama backend module is loaded correctly."""
    backend = _load_backend("ollama")
    assert hasattr(backend, "create_client")
    assert hasattr(backend, "attempt_generate")


def test_ollama_extract_text() -> None:
    """Tests that text is extracted from an Ollama response."""
    from unittest.mock import MagicMock  # noqa: PLC0415

    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.content = "Hello."
    assert ollama.extract_text(response) == "Hello."


def test_claude_translate(mocker: MockerFixture) -> None:
    """Tests that translate works with the claude backend."""
    mock_client = mocker.MagicMock()
    mocker.patch.object(anthropic, "create_client", return_value=mock_client)
    mocker.patch("koffee.translator.time.sleep")

    mock_response = mocker.MagicMock()
    mock_response.content = [mocker.MagicMock()]
    mock_response.content[0].text = (
        "1\n00:00:00,000 --> 00:00:06,360\nHello.\n\n"
        "2\n00:00:07,800 --> 00:00:10,740\nHow have you been?"
    )
    mock_client.messages.create.return_value = mock_response

    result = translate(
        SAMPLE_TRANSCRIPT, "en", api_key="test-key", translator="anthropic"
    )

    assert len(result) == len(SAMPLE_SEGMENTS)
    assert result[0].text == "Hello."
    assert result[1].text == "How have you been?"


# --- Ollama backend tests ---


def test_ollama_create_client_uses_local_endpoint(
    mocker: MockerFixture,
) -> None:
    """Tests the local endpoint, timeout, and disabled SDK retries."""
    mock_openai = mocker.patch("koffee.llm.ollama.OpenAI")

    ollama.create_client(api_key=None)

    mock_openai.assert_called_once_with(
        base_url=ollama.OLLAMA_BASE_URL,
        api_key="ollama",
        timeout=ollama.REQUEST_TIMEOUT_SECONDS,
        max_retries=0,
    )


def test_ollama_attempt_generate_success(mocker: MockerFixture) -> None:
    """Tests that a successful Ollama call returns the response."""
    mock_client = mocker.MagicMock()
    mock_response = mocker.MagicMock()
    mock_client.chat.completions.create.return_value = mock_response

    result = ollama.attempt_generate(mock_client, "prompt", "qwen3:14b", SYSTEM_PROMPT)

    assert result is mock_response


def test_ollama_attempt_generate_raises_on_error(mocker: MockerFixture) -> None:
    """Tests that errors from the Ollama client propagate out."""
    from openai import APIStatusError  # noqa: PLC0415

    mock_client = mocker.MagicMock()
    mock_response = mocker.MagicMock()
    mock_response.status_code = 400
    mock_response.headers = {}
    mock_response.json.return_value = {"error": {"message": "bad request"}}
    exc = APIStatusError(message="bad request", response=mock_response, body=None)
    mock_client.chat.completions.create.side_effect = exc

    with pytest.raises(APIStatusError):
        ollama.attempt_generate(mock_client, "prompt", "qwen3:14b", SYSTEM_PROMPT)


def test_ollama_is_retryable_rate_limit(mocker: MockerFixture) -> None:
    """Tests that a RateLimitError is classified as retryable."""
    from openai import RateLimitError as OpenAIRateLimitError  # noqa: PLC0415

    mock_response = mocker.MagicMock()
    mock_response.status_code = 429
    mock_response.headers = {}
    mock_response.json.return_value = {"error": {"message": "rate limited"}}
    exc = OpenAIRateLimitError(
        message="rate limited", response=mock_response, body=None
    )
    assert ollama.is_retryable(exc) is True


def test_ollama_is_retryable_connection_error(mocker: MockerFixture) -> None:
    """Tests that a connection error is classified as retryable."""
    from openai import APIConnectionError as OpenAIConnectionError  # noqa: PLC0415

    exc = OpenAIConnectionError(request=mocker.MagicMock())
    assert ollama.is_retryable(exc) is True


def test_ollama_is_retryable_5xx(mocker: MockerFixture) -> None:
    """Tests that a 5xx APIStatusError is classified as retryable."""
    from openai import APIStatusError  # noqa: PLC0415

    mock_response = mocker.MagicMock()
    mock_response.status_code = 503
    mock_response.headers = {}
    mock_response.json.return_value = {"error": {"message": "unavailable"}}
    exc = APIStatusError(message="unavailable", response=mock_response, body=None)
    assert ollama.is_retryable(exc) is True


def test_ollama_is_retryable_4xx_not_retryable(mocker: MockerFixture) -> None:
    """Tests that a non-429 4xx APIStatusError is classified as non-retryable."""
    from openai import APIStatusError  # noqa: PLC0415

    mock_response = mocker.MagicMock()
    mock_response.status_code = 400
    mock_response.headers = {}
    mock_response.json.return_value = {"error": {"message": "bad request"}}
    exc = APIStatusError(message="bad request", response=mock_response, body=None)
    assert ollama.is_retryable(exc) is False


def test_ollama_translate(mocker: MockerFixture) -> None:
    """Tests that translate works with the ollama backend."""
    mock_client = mocker.MagicMock()
    mocker.patch.object(ollama, "create_client", return_value=mock_client)
    mocker.patch("koffee.translator.time.sleep")

    mock_response = mocker.MagicMock()
    mock_response.choices = [mocker.MagicMock()]
    mock_response.choices[0].message.content = (
        "1\n00:00:00,000 --> 00:00:06,360\nHello.\n\n"
        "2\n00:00:07,800 --> 00:00:10,740\nHow have you been?"
    )
    mock_client.chat.completions.create.return_value = mock_response

    result = translate(SAMPLE_TRANSCRIPT, "en", api_key=None, translator="ollama")

    assert len(result) == len(SAMPLE_SEGMENTS)
    assert result[0].text == "Hello."
    assert result[1].text == "How have you been?"


def test_ollama_translate_uses_default_model(mocker: MockerFixture) -> None:
    """Tests that the default qwen3:14b model is used when none is specified."""
    mock_client = mocker.MagicMock()
    mocker.patch.object(ollama, "create_client", return_value=mock_client)
    mocker.patch("koffee.translator.time.sleep")

    mock_response = mocker.MagicMock()
    mock_response.choices = [mocker.MagicMock()]
    mock_response.choices[0].message.content = (
        "1\n00:00:00,000 --> 00:00:06,360\nHello.\n\n"
        "2\n00:00:07,800 --> 00:00:10,740\nHow have you been?"
    )
    mock_client.chat.completions.create.return_value = mock_response

    translate(SAMPLE_TRANSCRIPT, "en", api_key=None, translator="ollama")

    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    assert call_kwargs["model"] == "qwen3:14b"


# --- Chunk size tests ---


def test_chunk_segments_default_chunk_size() -> None:
    """Tests that _chunk_segments uses the default chunk size when none is given."""
    default_chunk_size = 200
    many_segments: list[Segment] = [
        Segment(start=float(i), end=float(i + 1), text="x")
        for i in range(default_chunk_size + 1)
    ]
    transcript: Transcript = Transcript(segments=many_segments, language="ja")

    chunks = _chunk_segments(transcript, "ko")

    expected_chunk_count = 2
    assert len(chunks) == expected_chunk_count
    assert len(chunks[0].segments) == default_chunk_size
    assert len(chunks[1].segments) == 1


def test_chunk_segments_explicit_chunk_size() -> None:
    """Tests that _chunk_segments respects an explicit chunk_size argument."""
    segments: list[Segment] = [
        Segment(start=float(i), end=float(i + 1), text="x") for i in range(10)
    ]
    transcript: Transcript = Transcript(segments=segments, language="ja")

    chunk_size = 3
    chunks = _chunk_segments(transcript, "ko", chunk_size=chunk_size)

    expected_chunk_count = 4
    assert len(chunks) == expected_chunk_count
    assert len(chunks[0].segments) == chunk_size
    assert len(chunks[-1].segments) == 1


def test_translate_uses_model_chunk_size(mocker: MockerFixture) -> None:
    """Tests that qwen3:14b uses its configured chunk size."""
    mock_client = mocker.MagicMock()
    mocker.patch.object(ollama, "create_client", return_value=mock_client)
    mocker.patch("koffee.translator.time.sleep")

    model = "qwen3:14b"
    model_chunk_size = 80
    many_segments: list[Segment] = [
        Segment(start=float(i), end=float(i + 1), text="x")
        for i in range(model_chunk_size + 1)
    ]

    first_response = mocker.MagicMock()
    first_response.choices = [mocker.MagicMock()]
    first_response.choices[0].message.content = "\n\n".join(
        (f"{entry_number}\n00:00:00,000 --> 00:00:01,000\nHello.")
        for entry_number in range(1, model_chunk_size + 1)
    )
    second_response = mocker.MagicMock()
    second_response.choices = [mocker.MagicMock()]
    second_response.choices[
        0
    ].message.content = f"{model_chunk_size + 1}\n00:00:00,000 --> 00:00:01,000\nHello."
    mock_client.chat.completions.create.side_effect = [
        first_response,
        second_response,
    ]

    translate(
        Transcript(segments=many_segments, language="ja"),
        "ko",
        api_key=None,
        translator="ollama",
        translation_model=model,
    )

    expected_request_count = 2
    assert mock_client.chat.completions.create.call_count == expected_request_count


def test_translate_explicit_chunk_size_overrides_model_default(
    mocker: MockerFixture,
) -> None:
    """Tests that an explicit chunk size overrides the model default."""
    mock_client = mocker.MagicMock()
    mocker.patch.object(ollama, "create_client", return_value=mock_client)
    mocker.patch("koffee.translator.time.sleep")

    segments: list[Segment] = [
        Segment(start=float(i), end=float(i + 1), text="x") for i in range(5)
    ]
    entries_by_chunk = ((1, 2), (3, 4), (5,))
    responses = []
    for entries in entries_by_chunk:
        response = mocker.MagicMock()
        response.choices = [mocker.MagicMock()]
        response.choices[0].message.content = "\n\n".join(
            (f"{entry_number}\n00:00:00,000 --> 00:00:01,000\nHello.")
            for entry_number in entries
        )
        responses.append(response)
    mock_client.chat.completions.create.side_effect = responses

    translate(
        Transcript(segments=segments, language="ja"),
        "ko",
        api_key=None,
        translator="ollama",
        translation_model="qwen3:14b",
        chunk_size=2,
    )

    assert mock_client.chat.completions.create.call_count == len(entries_by_chunk)


# --- Context size tests ---


def test_translate_uses_model_context_size(mocker: MockerFixture) -> None:
    """Tests that the qwen3:14b model uses its configured context window of 8."""
    mock_client = mocker.MagicMock()
    mocker.patch.object(ollama, "create_client", return_value=mock_client)
    mock_sleep = mocker.patch("koffee.translator.time.sleep")

    model = "qwen3:14b"
    model_context_size = 8

    segments: list[Segment] = [
        Segment(start=float(i), end=float(i + 1), text="x") for i in range(3)
    ]
    mock_response = mocker.MagicMock()
    mock_response.choices = [mocker.MagicMock()]
    mock_response.choices[0].message.content = "\n\n".join(
        f"{i + 1}\n00:00:0{i},000 --> 00:00:0{i + 1},000\nHello." for i in range(3)
    )
    mock_client.chat.completions.create.return_value = mock_response

    mock_build = mocker.patch("koffee.translator._build_prompt", return_value="prompt")

    translate(
        Transcript(segments=segments, language="ja"),
        "ko",
        api_key=None,
        translator="ollama",
        translation_model=model,
        chunk_size=3,
    )

    _, kwargs = mock_build.call_args
    assert len(kwargs["context_segments"]) <= model_context_size
    mock_sleep.assert_not_called()


def test_translate_explicit_context_size_overrides_model_default(
    mocker: MockerFixture,
) -> None:
    """Tests that an explicit context_size overrides the per-model default."""
    mock_client = mocker.MagicMock()
    mocker.patch.object(google, "create_client", return_value=mock_client)
    mocker.patch("koffee.translator.time.sleep")
    mocker.patch("koffee.translator.CHUNK_SIZE", 1)

    _configure_gemini_chunk_responses(mocker, mock_client)

    mock_build = mocker.patch("koffee.translator._build_prompt", return_value="prompt")
    mock_client.models.generate_content.return_value.text = (
        "1\n00:00:00,000 --> 00:00:01,000\nHello."
    )

    context_size = 2
    translate(
        SAMPLE_TRANSCRIPT,
        "en",
        api_key=None,
        translator="google",
        context_size=context_size,
    )

    for call in mock_build.call_args_list:
        _, kwargs = call
        assert len(kwargs["context_segments"]) <= context_size


def test_translate_uses_default_context_size_for_unknown_model(
    mocker: MockerFixture,
) -> None:
    """Tests that the default context size is used for unknown models."""
    mock_client = mocker.MagicMock()
    mocker.patch.object(google, "create_client", return_value=mock_client)
    mocker.patch("koffee.translator.time.sleep")

    mock_client.models.generate_content.return_value.text = (
        "1\n00:00:00,000 --> 00:00:06,360\nHello.\n\n"
        "2\n00:00:07,800 --> 00:00:10,740\nHow have you been?"
    )

    mock_build = mocker.patch("koffee.translator._build_prompt", return_value="prompt")

    translate(SAMPLE_TRANSCRIPT, "en", api_key=None, translator="google")

    default_context_size = 20
    _, kwargs = mock_build.call_args
    assert len(kwargs["context_segments"]) <= default_context_size
