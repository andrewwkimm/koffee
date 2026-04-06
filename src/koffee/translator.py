"""Text translator for koffee."""

import logging
import time
from collections.abc import Callable

from google import genai
from google.genai.errors import APIError, ClientError

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


def translate_transcript(
    transcript: dict,
    target_language: str,
    api_key: str | None,
    on_progress: Callable[[float], None] | None = None,
    translation_model: str = "gemini-2.5-flash",
) -> list:
    """Translates a transcript using Gemini, preserving timing information."""
    log.info("Translating transcript with Gemini.")

    client = genai.Client(api_key=api_key)
    chunks = _chunk_segments(transcript, target_language)
    translated_segments = _translate_chunks(
        client, chunks, on_progress, translation_model
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
    client,
    chunks: list[dict],
    on_progress: Callable[[float], None] | None,
    translation_model: str,
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
            client, prompt, chunk_data["chunk"], translation_model
        )
        translated_segments.extend(translated_chunk)

        if on_progress:
            on_progress((i + 1) / len(chunks))

        if i < len(chunks) - 1:
            time.sleep(SLEEP_BETWEEN_REQUESTS)

    return translated_segments


def _translate_chunk(
    client, prompt: str, chunk: list[dict], translation_model: str
) -> list[dict]:
    """Calls the LLM with a prompt and parses the response."""
    response = _call_with_retries(client, prompt, translation_model)
    translated_chunk = _parse_srt_response(response.text, chunk)

    return translated_chunk


def _call_with_retries(
    client, prompt: str, translation_model: str, max_retries: int = 3
):
    """Calls Gemini with exponential backoff on transient failures."""
    last_error = None
    for attempt in range(max_retries):
        result, error = _attempt_generate(client, prompt, translation_model)
        if result is not None:
            return result
        last_error = error
        if attempt < max_retries - 1:
            wait = 2 ** (attempt + 1)
            log.warning(f"Gemini request failed, retrying in {wait}s...")
            time.sleep(wait)

    raise last_error


def _attempt_generate(client, prompt: str, translation_model: str):
    """Makes a single Gemini API call, returning (response, None) or (None, error).

    Raises ClientError (4xx except 429) immediately since those are not retryable.
    """
    try:
        response = client.models.generate_content(
            model=translation_model,
            contents=prompt,
            config={"system_instruction": SYSTEM_PROMPT},
        )
    except ClientError as exc:
        if exc.code == 429:
            return None, exc
        raise
    except APIError as exc:
        return None, exc
    else:
        return response, None


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
        log.warning("Empty Gemini response, using original segments.")
        return list(original_segments)

    translated_segments = []
    blocks = [b.strip() for b in sanitized.split("\n\n") if b.strip()]

    if len(blocks) < len(original_segments):
        log.warning(
            f"Gemini returned {len(blocks)} blocks but expected "
            f"{len(original_segments)}; {len(original_segments) - len(blocks)} "
            "segments will be missing from output."
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
