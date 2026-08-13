"""Structural contract for LLM translation backends."""

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class TranslationProvider(Protocol):
    """Module-level contract for translation backends."""

    NAME: str
    DEFAULT_MODEL: str
    RETRYABLE_ERRORS: tuple[type[Exception], ...]

    @staticmethod
    def create_client(api_key: str | None) -> Any: ...

    @staticmethod
    def attempt_generate(
        client: Any,
        prompt: str,
        model: str,
        system_prompt: str,
    ) -> Any: ...

    @staticmethod
    def extract_text(response: Any) -> str: ...

    @staticmethod
    def is_retryable(error: Exception) -> bool: ...
