"""Ollama translation backend."""

from openai import APIConnectionError, APIStatusError, OpenAI, RateLimitError

OLLAMA_BASE_URL = "http://localhost:11434/v1"


def create_client(api_key: str | None):
    """Creates an Ollama client using the local OpenAI-compatible endpoint."""
    return OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama")


def attempt_generate(client, prompt: str, model: str, system_prompt: str):
    """Makes a single Ollama API call, returning (response, None) or (None, error).

    Raises APIStatusError for non-retryable client errors (4xx except 429).
    """
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
        )
    except RateLimitError as exc:
        return None, exc
    except APIConnectionError as exc:
        return None, exc
    except APIStatusError as exc:
        if 400 <= exc.status_code < 500:
            raise
        return None, exc
    else:
        return response, None
