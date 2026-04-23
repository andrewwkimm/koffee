"""ChatGPT translation backend."""

from openai import APIConnectionError, APIStatusError, OpenAI, RateLimitError

NAME = "chatgpt"
DEFAULT_MODEL = "gpt-4o"


def create_client(api_key: str | None):
    """Creates an OpenAI client."""
    return OpenAI(api_key=api_key)


def attempt_generate(client, prompt: str, model: str, system_prompt: str):
    """Makes a single OpenAI API call, returning the response."""
    return client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
    )


def extract_text(response) -> str:
    """Extracts the generated text from a ChatGPT response."""
    return response.choices[0].message.content


def is_retryable(exc: Exception) -> bool:
    """Returns True for transient OpenAI errors worth retrying."""
    if isinstance(exc, (RateLimitError, APIConnectionError)):
        return True
    if isinstance(exc, APIStatusError):
        return exc.status_code >= 500
    return False
