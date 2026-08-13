"""Ollama translation backend."""

from http import HTTPStatus

from openai import (
    APIConnectionError,
    APIStatusError,
    OpenAI,
    RateLimitError,
)

from koffee.exceptions import TranslationIntegrityError

OLLAMA_BASE_URL = "http://localhost:11434/v1"

NAME = "ollama"
DEFAULT_MODEL = "qwen3:14b"
REQUEST_TIMEOUT_SECONDS = 120.0
RETRYABLE_ERRORS = (
    RateLimitError,
    APIConnectionError,
    APIStatusError,
)


def create_client(api_key: str | None):
    """Creates an Ollama client with application-owned retries."""
    return OpenAI(
        base_url=OLLAMA_BASE_URL,
        api_key="ollama",
        timeout=REQUEST_TIMEOUT_SECONDS,
        max_retries=0,
    )


def attempt_generate(
    client,
    prompt: str,
    model: str,
    system_prompt: str,
):
    """Makes one Ollama API call."""
    return client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
    )


def extract_text(response) -> str:
    """Returns nonempty text from an Ollama response."""
    if not response.choices:
        error_message = "Ollama returned no choices."
        raise TranslationIntegrityError(error_message)

    content = response.choices[0].message.content
    if not isinstance(content, str) or not content.strip():
        error_message = "Ollama returned empty text."
        raise TranslationIntegrityError(error_message)
    return content


def is_retryable(error: Exception) -> bool:
    """Returns whether an Ollama error is transient."""
    if isinstance(
        error,
        (RateLimitError, APIConnectionError),
    ):
        return True
    if isinstance(error, APIStatusError):
        return error.status_code >= HTTPStatus.INTERNAL_SERVER_ERROR
    return False
