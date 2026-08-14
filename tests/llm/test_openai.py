"""Tests for the ChatGPT backend."""

import pytest
from pytest_mock import MockerFixture

from koffee.exceptions import TranslationIntegrityError
from koffee.llm import openai


def test_create_client_owns_retry_policy(
    mocker: MockerFixture,
) -> None:
    """Tests timeout and disabled SDK retries."""
    client = mocker.patch("koffee.llm.openai.OpenAI")

    openai.create_client("key")

    client.assert_called_once_with(
        api_key="key",
        timeout=openai.REQUEST_TIMEOUT_SECONDS,
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
        openai.extract_text(response)


def test_extract_text_rejects_empty_content(
    mocker: MockerFixture,
) -> None:
    """Tests rejection of an empty choice."""
    response = mocker.MagicMock()
    response.choices = [mocker.MagicMock()]
    response.choices[0].message.content = None

    with pytest.raises(
        TranslationIntegrityError,
        match="empty text",
    ):
        openai.extract_text(response)
