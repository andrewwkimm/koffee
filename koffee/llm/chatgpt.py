"""ChatGPT translation backend."""

from openai import APIConnectionError, APIStatusError, OpenAI, RateLimitError

NAME = "chatgpt"
DEFAULT_MODEL = "gpt-4o"


def create_client(api_key: str | None):
    """Creates an OpenAI client."""
    return OpenAI(api_key=api_key)


def extract_text(response) -> str:
    """Extracts the generated text from a ChatGPT response."""
    return response.choices[0].message.content


def attempt_generate(client, prompt: str, model: str, system_prompt: str):
    """Makes a single OpenAI API call, returning (response, None) or (None, error).

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
