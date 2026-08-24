"""Tests for the Gemini backend."""

import pytest
from pytest_mock import MockerFixture

from koffee.exceptions import TranslationIntegrityError, TranslationRefusedError
from koffee.llm import google


def test_create_client_sets_timeout(
    mocker: MockerFixture,
) -> None:
    """Tests the explicit Gemini request timeout."""
    client = mocker.patch("koffee.llm.google.genai.Client")

    google.create_client("key")

    assert client.call_args.kwargs["api_key"] == "key"
    options = client.call_args.kwargs["http_options"]
    assert options.timeout == google.REQUEST_TIMEOUT_MILLISECONDS


def test_attempt_generate_rejects_blocked_response(
    mocker: MockerFixture,
) -> None:
    """Tests that a safety-blocked response raises a non-retryable error."""
    client = mocker.MagicMock()
    response = mocker.MagicMock()
    response.candidates = []
    response.prompt_feedback.block_reason = "PROHIBITED_CONTENT"
    client.models.generate_content.return_value = response

    with pytest.raises(
        TranslationRefusedError,
        match="block_reason=PROHIBITED_CONTENT",
    ):
        google.attempt_generate(client, "prompt", "model", "system")


def test_attempt_generate_allows_missing_usage(
    mocker: MockerFixture,
) -> None:
    """Tests optional Gemini usage metadata."""
    client = mocker.MagicMock()
    response = mocker.MagicMock()
    response.candidates = [mocker.MagicMock()]
    response.usage_metadata = None
    client.models.generate_content.return_value = response

    result = google.attempt_generate(
        client,
        "prompt",
        "model",
        "system",
    )

    assert result is response


def test_extract_text_rejects_empty_text(
    mocker: MockerFixture,
) -> None:
    """Tests rejection of an empty Gemini response."""
    response = mocker.MagicMock(text="")

    with pytest.raises(
        TranslationIntegrityError,
        match="empty text",
    ):
        google.extract_text(response)
