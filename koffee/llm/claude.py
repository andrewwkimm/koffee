"""Claude translation backend."""

from anthropic import Anthropic, APIConnectionError, APIStatusError, RateLimitError


def create_client(api_key: str | None):
    """Creates an Anthropic client."""
    return Anthropic(api_key=api_key)


def attempt_generate(client, prompt: str, model: str, system_prompt: str):
    """Makes a single Claude API call, returning (response, None) or (None, error).

    Raises APIStatusError for non-retryable client errors (4xx except 429).
    """
    try:
        response = client.messages.create(
            model=model,
            max_tokens=8192,
            system=system_prompt,
            messages=[{"role": "user", "content": prompt}],
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
