"""Tests for the Ollama backend."""

import pytest
from pytest_mock import MockerFixture

from koffee.exceptions import TranslationIntegrityError
from koffee.llm import ollama


def test_create_client_owns_retry_policy(
    mocker: MockerFixture,
) -> None:
    """Tests timeout and disabled SDK retries."""
    client = mocker.patch("koffee.llm.ollama.OpenAI")

    ollama.create_client(None)

    client.assert_called_once_with(
        base_url=ollama.OLLAMA_BASE_URL,
        api_key="ollama",
        timeout=ollama.REQUEST_TIMEOUT_SECONDS,
        max_retries=0,
    )


def test_extract_text_rejects_missing_choices(
    mocker: MockerFixture,
) -> None:
    """Tests rejection of a response without choices."""
    response = mocker.MagicMock(choices=[])

    with pytest.raises(
        TranslationIntegrityError,
        match="no choices",
    ):
        ollama.extract_text(response)


def test_extract_text_rejects_empty_content(
    mocker: MockerFixture,
) -> None:
    """Tests rejection of an empty choice."""
    response = mocker.MagicMock()
    response.choices = [mocker.MagicMock()]
    response.choices[0].message.content = ""

    with pytest.raises(
        TranslationIntegrityError,
        match="empty text",
    ):
        ollama.extract_text(response)
