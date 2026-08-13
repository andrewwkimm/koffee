"""Tests for the Gemini backend."""

import pytest
from pytest_mock import MockerFixture

from koffee.exceptions import TranslationIntegrityError
from koffee.llm import gemini


def test_create_client_sets_timeout(
    mocker: MockerFixture,
) -> None:
    """Tests the explicit Gemini request timeout."""
    client = mocker.patch("koffee.llm.gemini.genai.Client")

    gemini.create_client("key")

    assert client.call_args.kwargs["api_key"] == "key"
    options = client.call_args.kwargs["http_options"]
    assert options.timeout == gemini.REQUEST_TIMEOUT_MILLISECONDS


def test_attempt_generate_allows_missing_usage(
    mocker: MockerFixture,
) -> None:
    """Tests optional Gemini usage metadata."""
    client = mocker.MagicMock()
    response = mocker.MagicMock()
    response.candidates = [mocker.MagicMock()]
    response.usage_metadata = None
    client.models.generate_content.return_value = response

    result = gemini.attempt_generate(
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
        gemini.extract_text(response)
