"""Retry helper with exponential backoff."""

import logging
import time
from collections.abc import Callable
from typing import TypeVar

log = logging.getLogger(__name__)

T = TypeVar("T")


def with_retries(
    fn: Callable[[], T],
    is_retryable: Callable[[Exception], bool],
    max_retries: int = 3,
) -> T:
    """Calls `fn` with exponential backoff on retryable exceptions.

    Non-retryable exceptions propagate immediately. After `max_retries` failed
    attempts, the last retryable exception is re-raised.
    """
    last_error: Exception | None = None
    for attempt in range(max_retries):
        try:
            return fn()
        except Exception as exc:
            if not is_retryable(exc):
                raise
            last_error = exc
            if attempt < max_retries - 1:
                wait = 2 ** (attempt + 1)
                log.warning(f"Retryable error, retrying in {wait}s: {exc}")
                time.sleep(wait)

    assert last_error is not None
    raise last_error
