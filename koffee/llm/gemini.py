"""Gemini translation backend."""

import logging

from google import genai
from google.genai.errors import APIError, ClientError

log = logging.getLogger(__name__)

NAME = "gemini"
DEFAULT_MODEL = "gemini-2.5-flash"


def create_client(api_key: str | None):
    """Creates a Gemini client."""
    return genai.Client(api_key=api_key)


def extract_text(response) -> str:
    """Extracts the generated text from a Gemini response."""
    return response.text


def attempt_generate(client, prompt: str, model: str, system_prompt: str):
    """Makes a single Gemini API call, returning the response."""
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config={
            "system_instruction": system_prompt,
        },
    )
    usage = response.usage_metadata
    log.debug(
        f"Gemini usage — prompt: {usage.prompt_token_count}, "
        f"output: {usage.candidates_token_count}, "
        f"thinking: {usage.thoughts_token_count}, "
        f"finish: {response.candidates[0].finish_reason}"
    )
    log.debug(f"Gemini response tail:\n{response.text[-500:]}")
    return response


def is_retryable(exc: Exception) -> bool:
    """Returns True for transient Gemini errors worth retrying."""
    if isinstance(exc, ClientError):
        return exc.code == 429
    return isinstance(exc, APIError)
