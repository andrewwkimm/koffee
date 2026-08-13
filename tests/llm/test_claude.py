"""Tests for the Claude backend."""

import pytest
from pytest_mock import MockerFixture

from koffee.exceptions import TranslationIntegrityError
from koffee.llm import claude


def test_create_client_owns_retry_policy(
    mocker: MockerFixture,
) -> None:
    """Tests timeout and disabled SDK retries."""
    client = mocker.patch("koffee.llm.claude.Anthropic")

    claude.create_client("key")

    client.assert_called_once_with(
        api_key="key",
        timeout=claude.REQUEST_TIMEOUT_SECONDS,
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

    assert claude.extract_text(response) == ("first\nsecond")


def test_extract_text_rejects_missing_text(
    mocker: MockerFixture,
) -> None:
    """Tests rejection of a response without text."""
    response = mocker.MagicMock(content=[])

    with pytest.raises(
        TranslationIntegrityError,
        match="no text blocks",
    ):
        claude.extract_text(response)
