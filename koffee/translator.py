"""Text translator for koffee."""

import logging
import re
import time
from collections.abc import Callable
from types import ModuleType

from koffee._retry import with_retries
from koffee.exceptions import TranslationIntegrityError
from koffee.llm._protocol import TranslationProvider
from koffee.schemas.domain import Segment, Transcript, TranslationChunk
from koffee.subtitle import segments_to_srt

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
    transcript: Transcript,
    target_language: str,
    api_key: str | None,
    on_progress: Callable[[float], None] | None = None,
    llm_model: str | None = None,
    prompt: str | None = None,
    provider: str = "gemini",
    chunk_size: int | None = None,
    context_size: int | None = None,
    sleep_requests: int | None = None,
) -> list[Segment]:
    """Translates a transcript using an LLM backend, preserving timing information."""
    log.info(f"Translating transcript with {provider}.")

    system_prompt = prompt if prompt else SYSTEM_PROMPT
    backend = _load_backend(provider)
    model = llm_model or backend.DEFAULT_MODEL
    resolved_chunk_size = (
        chunk_size
        if chunk_size is not None
        else CHUNK_SIZE_BY_MODEL.get(model, CHUNK_SIZE)
    )
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


def _chunk_segments(
    transcript: Transcript,
    target_language: str,
    chunk_size: int = CHUNK_SIZE,
) -> list[TranslationChunk]:
    """Validates and splits a transcript into immutable chunks."""
    validated_transcript = (
        transcript
        if isinstance(transcript, Transcript)
        else Transcript.model_validate(transcript)
    )

    chunks = [
        TranslationChunk(
            segments=validated_transcript.segments[index : index + chunk_size],
            source_language=validated_transcript.language,
            target_language=target_language,
            start_entry=index + 1,
        )
        for index in range(
            0,
            len(validated_transcript.segments),
            chunk_size,
        )
    ]
    return chunks


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


def _translate_chunks(
    backend: ModuleType,
    client,
    chunks: list[TranslationChunk],
    on_progress: Callable[[float], None] | None,
    llm_model: str,
    system_prompt: str,
    context_size: int = CONTEXT_SIZE,
    sleep_requests: int = SLEEP_REQUESTS,
) -> list[Segment]:
    """Translates validated chunks and reports progress."""
    log.info(f"Translating in {len(chunks)} chunks.")

    translated_segments = []
    for chunk_index, chunk_data in enumerate(chunks):
        chunk = list(chunk_data.segments)
        prompt = _build_prompt(
            chunk=chunk,
            source_language=chunk_data.source_language,
            target_language=chunk_data.target_language,
            start_entry=chunk_data.start_entry,
            context_segments=translated_segments[-context_size:],
        )
        translated_chunk = _translate_chunk(
            backend,
            client,
            prompt,
            chunk,
            llm_model,
            system_prompt,
            start_entry=chunk_data.start_entry,
        )
        translated_segments.extend(translated_chunk)

        if on_progress:
            on_progress((chunk_index + 1) / len(chunks))

        has_next_chunk = chunk_index < len(chunks) - 1
        if has_next_chunk and sleep_requests > 0:
            time.sleep(sleep_requests)

    return translated_segments


def _build_prompt(
    chunk: list[Segment],
    context_segments: list[Segment],
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

    end_entry = start_entry + len(chunk) - 1
    output_contract = (
        "Return only valid SRT blocks. "
        f"Use every entry ID from {start_entry} through {end_entry} exactly once, "
        "in ascending order. Preserve each timestamp exactly. Include no commentary "
        "or Markdown fences."
    )
    prompt_parts = [instruction, output_contract]

    if context_segments:
        context_start_entry = start_entry - len(context_segments)
        prompt_parts.extend(
            [
                f"The following {len(context_segments)} entries provide narrative "
                "context only. Do not include them in the output. "
                f"Begin the translation at entry {start_entry}.\n",
                "[CONTEXT - DO NOT TRANSLATE]\n",
                segments_to_srt(
                    context_segments,
                    start_entry=context_start_entry,
                ),
                "\n[TRANSLATE FROM HERE]\n",
            ]
        )

    prompt_parts.append(segments_to_srt(chunk, start_entry=start_entry))
    translation_prompt = "\n".join(prompt_parts)

    return translation_prompt


def _translate_chunk(
    backend: ModuleType,
    client,
    prompt: str,
    chunk: list[Segment],
    llm_model: str,
    system_prompt: str,
    start_entry: int,
) -> list[Segment]:
    """Calls the LLM with a prompt and parses the response."""
    response = with_retries(
        lambda: backend.attempt_generate(client, prompt, llm_model, system_prompt),
        backend.RETRYABLE_ERRORS,
        backend.is_retryable,
        max_retries=3,
    )
    response_text = backend.extract_text(response)
    translated_chunk = _parse_srt_response(response_text, chunk, start_entry)

    return translated_chunk


def _parse_srt_response(
    response_text: str | None,
    original_segments: list[Segment],
    start_entry: int = 1,
) -> list[Segment]:
    """Parses and validates an SRT response against the requested entries."""
    sanitized = _sanitize_response(response_text)
    if not sanitized:
        error_message = "Translation provider returned an empty response."
        raise TranslationIntegrityError(error_message)

    blocks = [
        block.strip() for block in re.split(r"\n{2,}", sanitized) if block.strip()
    ]
    translation_map = _blocks_to_translation_map(blocks)
    _validate_translation_entries(
        translation_map,
        start_entry=start_entry,
        entry_count=len(original_segments),
    )
    translated_segments = _merge_translated_segments(
        translation_map,
        original_segments,
        start_entry=start_entry,
    )
    return translated_segments


def _sanitize_response(response_text: str | None) -> str:
    """Strips thinking blocks and Markdown fences and normalizes line endings."""
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


def _blocks_to_translation_map(blocks: list[str]) -> dict[int, str]:
    """Parses structurally valid SRT blocks into translated text by entry ID."""
    translation_map: dict[int, str] = {}
    minimum_header_lines = 2
    timestamp_pattern = re.compile(
        r"\d{2}:\d{2}:\d{2}[,.]\d{3}\s*-->\s*"
        r"\d{2}:\d{2}:\d{2}[,.]\d{3}"
    )

    for block_number, block in enumerate(blocks, start=1):
        lines = block.split("\n")
        if len(lines) < minimum_header_lines:
            error_message = (
                f"Translation response block {block_number} is malformed: "
                "expected an entry ID, timestamp, and translated text."
            )
            raise TranslationIntegrityError(error_message)

        try:
            entry_number = int(lines[0].strip())
        except ValueError as exc:
            error_message = (
                f"Translation response block {block_number} has an invalid entry ID."
            )
            raise TranslationIntegrityError(error_message) from exc

        if timestamp_pattern.fullmatch(lines[1].strip()) is None:
            error_message = (
                f"Translation response entry {entry_number} has an invalid timestamp."
            )
            raise TranslationIntegrityError(error_message)

        translated_text = " ".join(line.strip() for line in lines[2:] if line.strip())
        if not translated_text:
            error_message = (
                f"Translation response entry {entry_number} has no translated text."
            )
            raise TranslationIntegrityError(error_message)
        if entry_number in translation_map:
            error_message = (
                f"Translation response contains duplicate entry ID {entry_number}."
            )
            raise TranslationIntegrityError(error_message)

        translation_map[entry_number] = translated_text

    return translation_map


def _validate_translation_entries(
    translation_map: dict[int, str],
    start_entry: int,
    entry_count: int,
) -> None:
    """Raises when translated entry IDs differ from the requested global IDs."""
    expected_entries = set(range(start_entry, start_entry + entry_count))
    actual_entries = set(translation_map)
    missing_entries = sorted(expected_entries - actual_entries)
    unexpected_entries = sorted(actual_entries - expected_entries)
    expected_order = list(range(start_entry, start_entry + entry_count))
    entries_are_reordered = list(translation_map) != expected_order

    problems = []
    if missing_entries:
        problems.append(f"missing entry IDs {missing_entries}")
    if unexpected_entries:
        problems.append(f"unexpected entry IDs {unexpected_entries}")
    if not missing_entries and not unexpected_entries and entries_are_reordered:
        problems.append("entry IDs are not in ascending order")
    if problems:
        details = "; ".join(problems)
        error_message = f"Translation response failed integrity validation: {details}."
        raise TranslationIntegrityError(error_message)


def _merge_translated_segments(
    translation_map: dict[int, str],
    original_segments: list[Segment],
    start_entry: int,
) -> list[Segment]:
    """Returns translated text with timing copied from the original segments."""
    merged_segments = []
    for entry_number, original in enumerate(original_segments, start=start_entry):
        merged_segments.append(
            Segment(
                start=original.start,
                end=original.end,
                text=translation_map[entry_number],
            )
        )
    return merged_segments
