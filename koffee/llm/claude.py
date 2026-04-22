"""Claude translation backend."""

from anthropic import Anthropic, APIConnectionError, APIStatusError, RateLimitError

NAME = "claude"
DEFAULT_MODEL = "claude-sonnet-4-6"


def create_client(api_key: str | None):
    """Creates an Anthropic client."""
    return Anthropic(api_key=api_key)


def extract_text(response) -> str:
    """Extracts the generated text from a Claude response."""
    return response.content[0].text


def attempt_generate(client, prompt: str, model: str, system_prompt: str):
    """Makes a single Claude API call, returning the response."""
    return client.messages.create(
        model=model,
        max_tokens=8192,
        system=system_prompt,
        messages=[{"role": "user", "content": prompt}],
    )


def is_retryable(exc: Exception) -> bool:
    """Returns True for transient Anthropic errors worth retrying."""
    if isinstance(exc, (RateLimitError, APIConnectionError)):
        return True
    if isinstance(exc, APIStatusError):
        return exc.status_code >= 500
    return False
