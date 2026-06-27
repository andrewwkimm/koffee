"""Tests for the generic retry helper."""

import pytest
from pytest_mock import MockerFixture

from koffee._retry import with_retries


class RetryableError(Exception):
    """Retryable test error."""


class TerminalError(Exception):
    """Non-retryable test error."""


def _is_retryable(exc: Exception) -> bool:
    return isinstance(exc, RetryableError)


def test_with_retries_returns_on_first_success(mocker: MockerFixture) -> None:
    """Tests that a successful call returns the result without retrying."""
    mock_retried_call = mocker.Mock(return_value="ok")

    result = with_retries(mock_retried_call, _is_retryable)

    assert result == "ok"
    mock_retried_call.assert_called_once()


def test_with_retries_retries_on_retryable_error(mocker: MockerFixture) -> None:
    """Tests that a retryable error triggers a retry and then succeeds."""
    mocker.patch("koffee._retry.time.sleep")
    mock_retried_call = mocker.Mock(side_effect=[RetryableError("flaky"), "ok"])

    result = with_retries(mock_retried_call, _is_retryable)

    assert result == "ok"
    expected_attempts = 2
    assert mock_retried_call.call_count == expected_attempts


def test_with_retries_propagates_non_retryable_immediately(
    mocker: MockerFixture,
) -> None:
    """Tests that a non-retryable error is raised without retrying."""
    mock_retried_call = mocker.Mock(side_effect=TerminalError("nope"))

    with pytest.raises(TerminalError):
        with_retries(mock_retried_call, _is_retryable)

    mock_retried_call.assert_called_once()


def test_with_retries_exhaustion_raises_last_error(mocker: MockerFixture) -> None:
    """Tests that after max_retries, the last retryable error is re-raised."""
    mocker.patch("koffee._retry.time.sleep")
    mock_retried_call = mocker.Mock(side_effect=RetryableError("still flaky"))

    with pytest.raises(RetryableError, match="still flaky"):
        with_retries(mock_retried_call, _is_retryable, max_retries=2)


def test_with_retries_uses_exponential_backoff(mocker: MockerFixture) -> None:
    """Tests that backoff doubles between retries."""
    mock_sleep = mocker.patch("koffee._retry.time.sleep")
    mock_retried_call = mocker.Mock(side_effect=RetryableError("flaky"))

    with pytest.raises(RetryableError):
        with_retries(mock_retried_call, _is_retryable, max_retries=3)

    assert [call.args[0] for call in mock_sleep.call_args_list] == [2, 4]
