"""Structural contract for translation providers."""

from typing import Any, Protocol


class Translator(Protocol):
    """Behavior required by a translation provider."""

    name: str
    default_model: str
    retryable_errors: tuple[type[Exception], ...]

    def create_client(
        self,
        api_key: str | None,
    ) -> Any:
        """Creates a provider SDK client."""
        ...

    def attempt_generate(
        self,
        client: Any,
        prompt: str,
        model: str,
        system_prompt: str,
    ) -> Any:
        """Makes one provider generation request."""
        ...

    def extract_text(
        self,
        response: Any,
    ) -> str:
        """Extracts translated text from a provider response."""
        ...

    def is_retryable(
        self,
        error: Exception,
    ) -> bool:
        """Returns whether a provider error is transient."""
        ...
