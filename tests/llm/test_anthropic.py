"""Tests for the Claude backend."""

import pytest
from pytest_mock import MockerFixture

from koffee.exceptions import TranslationIntegrityError
from koffee.llm import anthropic


def test_create_client_owns_retry_policy(
    mocker: MockerFixture,
) -> None:
    """Tests timeout and disabled SDK retries."""
    client = mocker.patch("koffee.llm.anthropic.Anthropic")

    anthropic.create_client("key")

    client.assert_called_once_with(
        api_key="key",
        timeout=anthropic.REQUEST_TIMEOUT_SECONDS,
        max_retries=0,
    )


def test_extract_text_combines_text_blocks(
    mocker: MockerFixture,
) -> None:
    """Tests inclusion of every Claude text block."""
    response = mocker.MagicMock()
    response.content = [
        mocker.MagicMock(text="first"),
        mocker.MagicMock(text=None),
        mocker.MagicMock(text="second"),
    ]

    assert anthropic.extract_text(response) == ("first\nsecond")


def test_extract_text_rejects_missing_text(
    mocker: MockerFixture,
) -> None:
    """Tests rejection of a response without text."""
    response = mocker.MagicMock(content=[])

    with pytest.raises(
        TranslationIntegrityError,
        match="no text blocks",
    ):
        anthropic.extract_text(response)
