"""Gemini translation backend."""

from google import genai
from google.genai.errors import APIError, ClientError


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
            config={"system_instruction": system_prompt},
        )
    except ClientError as exc:
        if exc.code == 429:
            return None, exc
        raise
    except APIError as exc:
        return None, exc
    else:
        return response, None
