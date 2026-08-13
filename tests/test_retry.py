"""Tests for the retry helper."""

import pytest
from pytest_mock import MockerFixture

from koffee._retry import with_retries


class RetryableError(Exception):
    """Retryable test error."""


class TerminalError(Exception):
    """Non-retryable test error."""


def _is_retryable(error: Exception) -> bool:
    """Returns whether an error is retryable."""
    return isinstance(error, RetryableError)


def test_with_retries_returns_on_first_success(
    mocker: MockerFixture,
) -> None:
    """Tests a successful initial attempt."""
    operation = mocker.Mock(return_value="ok")

    result = with_retries(
        operation,
        RetryableError,
        _is_retryable,
    )

    assert result == "ok"
    operation.assert_called_once()


def test_with_retries_retries_then_succeeds(
    mocker: MockerFixture,
) -> None:
    """Tests one retry after an initial failure."""
    mock_sleep = mocker.patch("koffee._retry.time.sleep")
    operation = mocker.Mock(side_effect=[RetryableError("flaky"), "ok"])

    result = with_retries(
        operation,
        RetryableError,
        _is_retryable,
    )

    assert result == "ok"
    expected_call_count = 2
    assert operation.call_count == expected_call_count
    mock_sleep.assert_called_once_with(2)


def test_with_retries_does_not_catch_unrelated_error(
    mocker: MockerFixture,
) -> None:
    """Tests unrelated exceptions bypass retry handling."""
    operation = mocker.Mock(side_effect=TerminalError("nope"))

    with pytest.raises(TerminalError, match="nope"):
        with_retries(
            operation,
            RetryableError,
            _is_retryable,
        )

    operation.assert_called_once()


def test_with_retries_propagates_rejected_error(
    mocker: MockerFixture,
) -> None:
    """Tests policy rejection of an eligible error."""
    operation = mocker.Mock(side_effect=RetryableError("nope"))

    with pytest.raises(RetryableError, match="nope"):
        with_retries(
            operation,
            RetryableError,
            lambda error: False,
        )

    operation.assert_called_once()


def test_with_retries_counts_additional_attempts(
    mocker: MockerFixture,
) -> None:
    """Tests retries exclude the initial attempt."""
    mock_sleep = mocker.patch("koffee._retry.time.sleep")
    operation = mocker.Mock(side_effect=RetryableError("still flaky"))

    with pytest.raises(
        RetryableError,
        match="still flaky",
    ):
        with_retries(
            operation,
            RetryableError,
            _is_retryable,
            max_retries=2,
        )

    expected_call_count = 3
    assert operation.call_count == expected_call_count
    assert [call.args[0] for call in mock_sleep.call_args_list] == [2, 4]


def test_with_retries_rejects_negative_retry_count(
    mocker: MockerFixture,
) -> None:
    """Tests rejection of negative retry counts."""
    operation = mocker.Mock()

    with pytest.raises(
        ValueError,
        match="must be non-negative",
    ):
        with_retries(
            operation,
            RetryableError,
            _is_retryable,
            max_retries=-1,
        )

    operation.assert_not_called()
