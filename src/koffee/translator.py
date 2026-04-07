"""Text translator for koffee."""

import logging
import time
from collections.abc import Callable
from types import ModuleType

from koffee.utils import convert_to_timestamp

log = logging.getLogger(__name__)

CHUNK_SIZE = 600
CONTEXT_ENTRIES = 25
SLEEP_BETWEEN_REQUESTS = 4

SYSTEM_PROMPT = """You are a professional subtitle translator specializing in Korean
dramas and Japanese anime. Your translations should feel like they were written
natively in English - natural, idiomatic, and faithful to the speaker's personality and
tone rather than the literal words.

Guidelines:
- Preserve each speaker's voice - formal characters stay formal, casual characters \
stay casual
- Adapt honorifics and speech levels to convey the relationship dynamic in natural
English rather than translating them literally
- Use modern English vernacular for slang and casual speech - avoid stiff or awkward \
phrasing
- Preserve emotional nuance - exclamations, hesitations, and sentence-final particles \
should feel natural in English
- Never sacrifice readability for literalness
- Preserve all subtitle entry numbers and timing markers exactly as given
- Translate only the text content, never the timestamps or entry numbers"""

BACKENDS = {
    "gemini": "koffee.llm.gemini",
    "chatgpt": "koffee.llm.chatgpt",
    "claude": "koffee.llm.claude",
}

DEFAULT_MODELS = {
    "gemini": "gemini-2.5-flash",
    "chatgpt": "gpt-4o",
    "claude": "claude-sonnet-4-20250514",
}


def _load_backend(backend_name: str) -> ModuleType:
    """Loads a translation backend module by name."""
    import importlib  # noqa: PLC0415

    module_path = BACKENDS.get(backend_name)
    if module_path is None:
        available = ", ".join(sorted(BACKENDS.keys()))
        error_message = (
            f"Unknown translation backend: {backend_name!r}. "
            f"Available backends: {available}"
        )
        raise ValueError(error_message)

    return importlib.import_module(module_path)


def _extract_text(response, backend_name: str) -> str:
    """Extracts text content from a backend-specific response object."""
    if backend_name == "gemini":
        return response.text
    if backend_name == "chatgpt":
        return response.choices[0].message.content
    if backend_name == "claude":
        return response.content[0].text
    return str(response)


def translate_transcript(
    transcript: dict,
    target_language: str,
    api_key: str | None,
    on_progress: Callable[[float], None] | None = None,
    translation_model: str | None = None,
    translation_prompt: str | None = None,
    translation_backend: str = "gemini",
) -> list:
    """Translates a transcript using an LLM backend, preserving timing information."""
    log.info(f"Translating transcript with {translation_backend}.")

    system_prompt = translation_prompt if translation_prompt else SYSTEM_PROMPT
    model = translation_model or DEFAULT_MODELS.get(translation_backend, "")
    backend = _load_backend(translation_backend)
    client = backend.create_client(api_key)
    chunks = _chunk_segments(transcript, target_language)
    translated_segments = _translate_chunks(
        backend,
        backend_name=translation_backend,
        client=client,
        chunks=chunks,
        on_progress=on_progress,
        translation_model=model,
        system_prompt=system_prompt,
    )
    return translated_segments


def _chunk_segments(transcript: dict, target_language: str) -> list[dict]:
    """Splits transcript segments into prompt-ready chunks."""
    segments = transcript["segments"]
    source_language = transcript["language"]

    chunks = [
        {
            "chunk": segments[i : i + CHUNK_SIZE],
            "source_language": source_language,
            "target_language": target_language,
            "start_entry": i * CHUNK_SIZE + 1,
        }
        for i in range(0, len(segments), CHUNK_SIZE)
    ]

    return chunks


def _translate_chunks(
    backend: ModuleType,
    backend_name: str,
    client,
    chunks: list[dict],
    on_progress: Callable[[float], None] | None,
    translation_model: str,
    system_prompt: str,
) -> list[dict]:
    """Iterates chunks, translating each and reporting progress."""
    log.info(f"Translating in {len(chunks)} chunks.")

    translated_segments = []
    for i, chunk_data in enumerate(chunks):
        prompt = _build_prompt(
            **chunk_data,
            context_entries=translated_segments[-CONTEXT_ENTRIES:],
        )
        translated_chunk = _translate_chunk(
            backend,
            backend_name,
            client,
            prompt,
            chunk_data["chunk"],
            translation_model,
            system_prompt,
        )
        translated_segments.extend(translated_chunk)

        if on_progress:
            on_progress((i + 1) / len(chunks))

        if i < len(chunks) - 1:
            time.sleep(SLEEP_BETWEEN_REQUESTS)

    return translated_segments


def _translate_chunk(
    backend: ModuleType,
    backend_name: str,
    client,
    prompt: str,
    chunk: list[dict],
    translation_model: str,
    system_prompt: str,
) -> list[dict]:
    """Calls the LLM with a prompt and parses the response."""
    response = _call_with_retries(
        backend, client, prompt, translation_model, system_prompt
    )
    response_text = _extract_text(response, backend_name)
    translated_chunk = _parse_srt_response(response_text, chunk)

    return translated_chunk


def _call_with_retries(
    backend: ModuleType,
    client,
    prompt: str,
    translation_model: str,
    system_prompt: str,
    max_retries: int = 3,
):
    """Calls an LLM backend with exponential backoff on transient failures."""
    last_error = None
    for attempt in range(max_retries):
        result, error = backend.attempt_generate(
            client, prompt, translation_model, system_prompt
        )
        if result is not None:
            return result
        last_error = error
        if attempt < max_retries - 1:
            wait = 2 ** (attempt + 1)
            log.warning(f"LLM request failed, retrying in {wait}s...")
            time.sleep(wait)

    raise last_error


def _segments_to_srt(segments: list[dict]) -> str:
    """Converts a list of segments to SRT format string."""
    lines = []
    for i, seg in enumerate(segments, 1):
        start = convert_to_timestamp(seg["start"], "srt")
        end = convert_to_timestamp(seg["end"], "srt")
        lines.append(f"{i}\n{start} --> {end}\n{seg['text'].strip()}\n")

    srt_text = "\n".join(lines)
    return srt_text


def _sanitize_response(response_text: str | None) -> str:
    """Strips markdown fences and normalizes line endings from LLM output."""
    if not response_text:
        return ""

    text = response_text.replace("\r\n", "\n").strip()

    if text.startswith("```"):
        first_newline = text.find("\n")
        if first_newline != -1:
            text = text[first_newline + 1 :]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

    return text


def _parse_srt_response(
    response_text: str | None, original_segments: list[dict]
) -> list[dict]:
    """Parses SRT formatted response back into segments."""
    MIN_SRT_BLOCK_LINES = 3

    sanitized = _sanitize_response(response_text)
    if not sanitized:
        log.warning("Empty LLM response, using original segments.")
        return list(original_segments)

    translated_segments = []
    blocks = [b.strip() for b in sanitized.split("\n\n") if b.strip()]

    if len(blocks) != len(original_segments):
        log.warning(
            f"LLM returned {len(blocks)} blocks but expected "
            f"{len(original_segments)}; output may have missing or extra segments."
        )

    for block, original in zip(blocks, original_segments, strict=False):
        lines = block.split("\n")
        if len(lines) < MIN_SRT_BLOCK_LINES:
            log.warning("Unexpected SRT block format, using original text.")
            translated_segments.append(original)
            continue

        text = " ".join(lines[2:])
        translated_segments.append(
            {
                "start": original["start"],
                "end": original["end"],
                "text": text,
            }
        )

    return translated_segments


def _build_prompt(
    chunk: list[dict],
    context_entries: list[dict],
    source_language: str,
    target_language: str,
    start_entry: int,
) -> str:
    """Builds the translation prompt for a chunk of subtitle entries."""
    if source_language == "auto":
        instruction = f"Translate the following subtitle entries to {target_language}."
    else:
        instruction = (
            f"Translate the following subtitle entries from "
            f"{source_language} to {target_language}."
        )

    prompt_parts = [instruction]

    if context_entries:
        prompt_parts.extend(
            [
                f"The following {len(context_entries)} entries are provided as context "
                "only to maintain narrative continuity. Do not include them in your "
                "translation."
                f" output. Begin your translation from entry {start_entry} only.\n",
                "[CONTEXT - DO NOT TRANSLATE]\n",
                _segments_to_srt(context_entries),
                "\n[TRANSLATE FROM HERE]\n",
            ]
        )

    prompt_parts.append(_segments_to_srt(chunk))
    translation_prompt = "\n".join(prompt_parts)

    return translation_prompt
