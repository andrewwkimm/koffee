"""Text translator for koffee."""

import logging
import time
from collections.abc import Callable
from types import ModuleType

from koffee.llm._protocol import TranslationProvider
from koffee.utils import convert_to_timestamp, with_retries

log = logging.getLogger(__name__)

CHUNK_SIZE = 200
CONTEXT_SIZE = 20
SLEEP_REQUESTS = 4

SLEEP_REQUESTS_BY_PROVIDER: dict[str, int] = {
    "ollama": 0,
}

CHUNK_SIZE_BY_MODEL: dict[str, int] = {
    "qwen3:8b": 40,
    "qwen3:14b": 80,
    "qwen3:32b": 150,
    "llama3.2": 80,
    "llama3.3": 150,
    "mistral": 80,
}

CONTEXT_SIZE_BY_MODEL: dict[str, int] = {
    "qwen3:8b": 5,
    "qwen3:14b": 8,
    "qwen3:32b": 12,
    "llama3.2": 8,
    "llama3.3": 12,
    "mistral": 8,
}

SYSTEM_PROMPT = """You are a professional subtitle translator specializing in Korean
dramas and Japanese anime. Your translations should feel natural and idiomatic in the
target language - faithful to the speaker's personality and tone rather than the literal
words.

Guidelines:
- Preserve each speaker's voice - formal characters stay formal, casual characters \
stay casual
- Adapt honorifics and speech levels to convey the relationship dynamic naturally in \
the target language rather than translating them literally
- Use natural vernacular for slang and casual speech - avoid stiff or awkward phrasing
- Preserve emotional nuance - exclamations, hesitations, and sentence-final particles \
should feel natural in the target language
- Never sacrifice readability for literalness
- Preserve all subtitle entry numbers and timing markers exactly as given
- Translate only the text content, never the timestamps or entry numbers"""

LLM = {
    "gemini": "koffee.llm.gemini",
    "chatgpt": "koffee.llm.chatgpt",
    "claude": "koffee.llm.claude",
    "ollama": "koffee.llm.ollama",
}


def translate(
    transcript: dict,
    target_language: str,
    api_key: str | None,
    on_progress: Callable[[float], None] | None = None,
    llm_model: str | None = None,
    prompt: str | None = None,
    provider: str = "gemini",
    chunk_size: int | None = None,
    context_size: int | None = None,
    sleep_requests: int | None = None,
) -> list:
    """Translates a transcript using an LLM backend, preserving timing information."""
    log.info(f"Translating transcript with {provider}.")

    system_prompt = prompt if prompt else SYSTEM_PROMPT
    backend = _load_backend(provider)
    model = llm_model or backend.DEFAULT_MODEL
    resolved_chunk_size = chunk_size or CHUNK_SIZE_BY_MODEL.get(model, CHUNK_SIZE)
    resolved_context_size = (
        context_size
        if context_size is not None
        else CONTEXT_SIZE_BY_MODEL.get(model, CONTEXT_SIZE)
    )
    resolved_sleep_requests = (
        sleep_requests
        if sleep_requests is not None
        else SLEEP_REQUESTS_BY_PROVIDER.get(provider, SLEEP_REQUESTS)
    )
    client = backend.create_client(api_key)
    chunks = _chunk_segments(transcript, target_language, resolved_chunk_size)
    translated_segments = _translate_chunks(
        backend,
        client=client,
        chunks=chunks,
        on_progress=on_progress,
        llm_model=model,
        system_prompt=system_prompt,
        context_size=resolved_context_size,
        sleep_requests=resolved_sleep_requests,
    )
    return translated_segments


def _load_backend(backend_name: str) -> TranslationProvider:
    """Loads a translation backend module by name."""
    import importlib  # noqa: PLC0415

    module_path = LLM.get(backend_name)
    if module_path is None:
        available = ", ".join(sorted(LLM.keys()))
        error_message = (
            f"Unknown translation backend: {backend_name!r}. Available LLM: {available}"
        )
        raise ValueError(error_message)

    return importlib.import_module(module_path)


def _chunk_segments(
    transcript: dict, target_language: str, chunk_size: int = CHUNK_SIZE
) -> list[dict]:
    """Splits transcript segments into prompt-ready chunks."""
    segments = transcript["segments"]
    source_language = transcript["language"]

    chunks = [
        {
            "chunk": segments[i : i + chunk_size],
            "source_language": source_language,
            "target_language": target_language,
            "start_entry": i * chunk_size + 1,
        }
        for i in range(0, len(segments), chunk_size)
    ]

    return chunks


def _translate_chunks(
    backend: ModuleType,
    client,
    chunks: list[dict],
    on_progress: Callable[[float], None] | None,
    llm_model: str,
    system_prompt: str,
    context_size: int = CONTEXT_SIZE,
    sleep_requests: int = SLEEP_REQUESTS,
) -> list[dict]:
    """Iterates chunks, translating each and reporting progress."""
    log.info(f"Translating in {len(chunks)} chunks.")

    translated_segments = []
    for i, chunk_data in enumerate(chunks):
        prompt = _build_prompt(
            **chunk_data,
            context_segments=translated_segments[-context_size:],
        )
        translated_chunk = _translate_chunk(
            backend,
            client,
            prompt,
            chunk_data["chunk"],
            llm_model,
            system_prompt,
        )
        translated_segments.extend(translated_chunk)

        if on_progress:
            on_progress((i + 1) / len(chunks))

        if i < len(chunks) - 1 and sleep_requests > 0:
            time.sleep(sleep_requests)

    return translated_segments


def _translate_chunk(
    backend: ModuleType,
    client,
    prompt: str,
    chunk: list[dict],
    llm_model: str,
    system_prompt: str,
) -> list[dict]:
    """Calls the LLM with a prompt and parses the response."""
    response = _call_with_retries(backend, client, prompt, llm_model, system_prompt)
    response_text = backend.extract_text(response)
    translated_chunk = _parse_srt_response(response_text, chunk)

    return translated_chunk


def _call_with_retries(
    backend: ModuleType,
    client,
    prompt: str,
    llm_model: str,
    system_prompt: str,
    max_retries: int = 3,
):
    """Calls an LLM backend with exponential backoff on transient failures."""
    return with_retries(
        lambda: backend.attempt_generate(client, prompt, llm_model, system_prompt),
        backend.is_retryable,
        max_retries=max_retries,
    )


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
    """Strips thinking blocks, markdown fences, and normalizes line endings."""
    if not response_text:
        return ""

    text = response_text.replace("\r\n", "\n").strip()

    if "<think>" in text:
        end = text.find("</think>")
        if end != -1:
            text = text[end + len("</think>") :].strip()
        else:
            text = text[text.find("<think>") + len("<think>") :].strip()

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
    """Parses SRT formatted response back into segments.

    Matches blocks to original segments by entry number rather than position,
    so skipped or reordered entries fall back to the original text instead of
    misaligning all subsequent entries.
    """
    sanitized = _sanitize_response(response_text)
    if not sanitized:
        log.warning("Empty LLM response, using original segments.")
        return list(original_segments)

    blocks = [b.strip() for b in sanitized.split("\n\n") if b.strip()]

    if len(blocks) != len(original_segments):
        log.warning(
            f"LLM returned {len(blocks)} blocks but expected "
            f"{len(original_segments)}; output may have missing or extra segments."
        )

    translation_map = _blocks_to_translation_map(blocks)
    return _merge_translated_segments(translation_map, original_segments)


def _blocks_to_translation_map(blocks: list[str]) -> dict[int, str]:
    """Parses SRT blocks into a {entry_number: translated_text} mapping."""
    translation_map: dict[int, str] = {}
    for block in blocks:
        lines = block.split("\n")
        if len(lines) < 3:
            continue
        try:
            entry_num = int(lines[0].strip())
        except ValueError:
            continue
        translation_map[entry_num] = " ".join(lines[2:])
    return translation_map


def _merge_translated_segments(
    translation_map: dict[int, str], original_segments: list[dict]
) -> list[dict]:
    """Merges translated text onto original segments."""
    merged_segments = []
    for i, original in enumerate(original_segments, start=1):
        translated_text = translation_map.get(i)
        if translated_text is None:
            log.debug(f"Entry {i} missing from LLM response, using original text.")
            merged_segments.append(original)
        else:
            merged_segments.append(
                {
                    "start": original["start"],
                    "end": original["end"],
                    "text": translated_text,
                }
            )
    return merged_segments


def _build_prompt(
    chunk: list[dict],
    context_segments: list[dict],
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

    if context_segments:
        prompt_parts.extend(
            [
                f"The following {len(context_segments)} entries are provided as "
                "context only to maintain narrative continuity. Do not include them "
                "in your translation."
                f" output. Begin your translation from entry {start_entry} only.\n",
                "[CONTEXT - DO NOT TRANSLATE]\n",
                _segments_to_srt(context_segments),
                "\n[TRANSLATE FROM HERE]\n",
            ]
        )

    prompt_parts.append(_segments_to_srt(chunk))
    translation_prompt = "\n".join(prompt_parts)

    return translation_prompt
