"""Gemini translation backend."""

import logging
from http import HTTPStatus

from google import genai
from google.genai import types
from google.genai.errors import APIError, ClientError

from koffee.exceptions import TranslationIntegrityError

log = logging.getLogger(__name__)

NAME = "gemini"
DEFAULT_MODEL = "gemini-2.5-flash"
REQUEST_TIMEOUT_MILLISECONDS = 120_000
RETRYABLE_ERRORS = (APIError,)


def create_client(api_key: str | None):
    """Creates a Gemini client with a request timeout."""
    options = types.HttpOptions(timeout=REQUEST_TIMEOUT_MILLISECONDS)
    return genai.Client(
        api_key=api_key,
        http_options=options,
    )


def attempt_generate(
    client,
    prompt: str,
    model: str,
    system_prompt: str,
):
    """Makes one Gemini API call."""
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config={"system_instruction": system_prompt},
    )
    if not response.candidates:
        feedback = getattr(
            response,
            "prompt_feedback",
            None,
        )
        block_reason = getattr(
            feedback,
            "block_reason",
            "unknown",
        )
        error_message = f"Gemini returned no candidates (block_reason={block_reason})."
        raise TranslationIntegrityError(error_message)

    usage = getattr(response, "usage_metadata", None)
    if usage is not None:
        log.debug(
            "Gemini usage: prompt=%s output=%s thinking=%s finish=%s",
            getattr(
                usage,
                "prompt_token_count",
                None,
            ),
            getattr(
                usage,
                "candidates_token_count",
                None,
            ),
            getattr(
                usage,
                "thoughts_token_count",
                None,
            ),
            getattr(
                response.candidates[0],
                "finish_reason",
                None,
            ),
        )
    return response


def extract_text(response) -> str:
    """Returns nonempty text from a Gemini response."""
    text = getattr(response, "text", None)
    if not isinstance(text, str) or not text.strip():
        error_message = "Gemini returned empty text."
        raise TranslationIntegrityError(error_message)
    return text


def is_retryable(error: Exception) -> bool:
    """Returns whether a Gemini error is transient."""
    if isinstance(error, ClientError):
        return error.code == HTTPStatus.TOO_MANY_REQUESTS
    return isinstance(error, APIError)
