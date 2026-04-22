"""Tests for the generic retry helper."""

import pytest
from pytest_mock import MockerFixture

from koffee.utils import with_retries


class RetryableError(Exception):
    """Retryable test error."""


class TerminalError(Exception):
    """Non-retryable test error."""


def _is_retryable(exc: Exception) -> bool:
    return isinstance(exc, RetryableError)


def test_with_retries_returns_on_first_success() -> None:
    """Tests that a successful call returns the result without retrying."""
    calls = {"n": 0}

    def fn():
        calls["n"] += 1
        return "ok"

    result = with_retries(fn, _is_retryable)

    assert result == "ok"
    assert calls["n"] == 1


def test_with_retries_retries_on_retryable_error(mocker: MockerFixture) -> None:
    """Tests that a retryable error triggers a retry and then succeeds."""
    mocker.patch("koffee.utils.retry.time.sleep")
    attempts = {"n": 0}

    def fn():
        attempts["n"] += 1
        if attempts["n"] < 2:
            raise RetryableError("flaky")
        return "ok"

    result = with_retries(fn, _is_retryable)

    assert result == "ok"
    assert attempts["n"] == 2


def test_with_retries_propagates_non_retryable_immediately() -> None:
    """Tests that a non-retryable error is raised without retrying."""
    attempts = {"n": 0}

    def fn():
        attempts["n"] += 1
        raise TerminalError("nope")

    with pytest.raises(TerminalError):
        with_retries(fn, _is_retryable)

    assert attempts["n"] == 1


def test_with_retries_exhaustion_raises_last_error(mocker: MockerFixture) -> None:
    """Tests that after max_retries, the last retryable error is re-raised."""
    mocker.patch("koffee.utils.retry.time.sleep")

    def fn():
        raise RetryableError("still flaky")

    with pytest.raises(RetryableError, match="still flaky"):
        with_retries(fn, _is_retryable, max_retries=2)


def test_with_retries_uses_exponential_backoff(mocker: MockerFixture) -> None:
    """Tests that backoff doubles between retries."""
    mock_sleep = mocker.patch("koffee.utils.retry.time.sleep")

    def fn():
        raise RetryableError("flaky")

    with pytest.raises(RetryableError):
        with_retries(fn, _is_retryable, max_retries=3)

    assert [call.args[0] for call in mock_sleep.call_args_list] == [2, 4]
