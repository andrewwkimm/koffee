"""Gemini translation backend."""

import logging

from google import genai
from google.genai.errors import APIError, ClientError

log = logging.getLogger(__name__)


def create_client(api_key: str | None):
    """Creates a Gemini client."""
    return genai.Client(api_key=api_key)


def attempt_generate(client, prompt: str, model: str, system_prompt: str):
    """Makes a single Gemini API call, returning (response, None) or (None, error).

    Raises ClientError (4xx except 429) immediately since those are not retryable.
    """
    try:
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config={
                "system_instruction": system_prompt,
            },
        )
    except ClientError as exc:
        if exc.code == 429:
            return None, exc
        raise
    except APIError as exc:
        return None, exc
    else:
        usage = response.usage_metadata
        log.debug(
            f"Gemini usage — prompt: {usage.prompt_token_count}, "
            f"output: {usage.candidates_token_count}, "
            f"thinking: {usage.thoughts_token_count}, "
            f"finish: {response.candidates[0].finish_reason}"
        )
        log.debug(f"Gemini response tail:\n{response.text[-500:]}")
        return response, None
