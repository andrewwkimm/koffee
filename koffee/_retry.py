"""Retry operations with exponential backoff."""

import logging
import time
from collections.abc import Callable
from typing import TypeVar

log = logging.getLogger(__name__)

T = TypeVar("T")
RetryableErrors = type[Exception] | tuple[type[Exception], ...]


def with_retries(
    operation: Callable[[], T],
    retryable_errors: RetryableErrors,
    is_retryable: Callable[[Exception], bool],
    max_retries: int = 3,
) -> T:
    """Runs an operation once plus the configured retry count.

    Args:
        operation: Operation to run.
        retryable_errors: Exception types eligible for retry.
        is_retryable: Policy for classifying eligible exceptions.
        max_retries: Additional attempts after the initial call.

    Raises:
        ValueError: ``max_retries`` is negative.
    """
    if max_retries < 0:
        error_message = f"max_retries must be non-negative, got {max_retries}."
        raise ValueError(error_message)

    retry_number = 0
    while True:
        try:
            return operation()
        except retryable_errors as error:
            retries_exhausted = retry_number == max_retries
            if retries_exhausted or not is_retryable(error):
                raise

            retry_number += 1
            wait_seconds = 2**retry_number
            log.warning(
                "Retryable error, retrying in %ss: %s",
                wait_seconds,
                error,
            )
            time.sleep(wait_seconds)
