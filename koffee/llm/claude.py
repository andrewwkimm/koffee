"""Claude translation backend."""

from http import HTTPStatus

from anthropic import (
    Anthropic,
    APIConnectionError,
    APIStatusError,
    RateLimitError,
)

from koffee.exceptions import TranslationIntegrityError

NAME = "claude"
DEFAULT_MODEL = "claude-sonnet-4-6"
REQUEST_TIMEOUT_SECONDS = 120.0
RETRYABLE_ERRORS = (
    RateLimitError,
    APIConnectionError,
    APIStatusError,
)


def create_client(api_key: str | None):
    """Creates an Anthropic client with application-owned retries."""
    return Anthropic(
        api_key=api_key,
        timeout=REQUEST_TIMEOUT_SECONDS,
        max_retries=0,
    )


def attempt_generate(
    client,
    prompt: str,
    model: str,
    system_prompt: str,
):
    """Makes one Anthropic API call."""
    return client.messages.create(
        model=model,
        max_tokens=8192,
        system=system_prompt,
        messages=[{"role": "user", "content": prompt}],
    )


def extract_text(response) -> str:
    """Combines every nonempty Claude text block."""
    text_blocks = []
    for block in response.content:
        text = getattr(block, "text", None)
        if isinstance(text, str) and text.strip():
            text_blocks.append(text)

    if not text_blocks:
        error_message = "Claude returned no text blocks."
        raise TranslationIntegrityError(error_message)
    return "\n".join(text_blocks)


def is_retryable(error: Exception) -> bool:
    """Returns whether an Anthropic error is transient."""
    if isinstance(
        error,
        (RateLimitError, APIConnectionError),
    ):
        return True
    if isinstance(error, APIStatusError):
        return error.status_code >= HTTPStatus.INTERNAL_SERVER_ERROR
    return False
