"""Text translator for koffee."""

import logging
import time

from google import genai

from koffee.utils import convert_to_timestamp

log = logging.getLogger(__name__)

CHUNK_SIZE = 300
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
    transcript: dict, target_language: str, api_key: str | None
) -> list:
    """Translates a transcript using Gemini, preserving timing information."""
    log.info("Translating transcript with Gemini.")

    client = genai.Client(api_key=api_key)

    segments = transcript["segments"]
    source_language = transcript["language"]
    chunks = [segments[i : i + CHUNK_SIZE] for i in range(0, len(segments), CHUNK_SIZE)]

    log.info(f"Translating {len(segments)} entries in {len(chunks)} chunks.")

    translated_segments = []

    for i, chunk in enumerate(chunks):
        context_entries = (
            translated_segments[-CONTEXT_ENTRIES:] if translated_segments else []
        )

        prompt = _build_prompt(
            chunk=chunk,
            context_entries=context_entries,
            source_language=source_language,
            target_language=target_language,
            start_entry=i * CHUNK_SIZE + 1,
        )

        log.info(f"Translating chunk {i + 1}/{len(chunks)}.")
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config={
                "system_instruction": SYSTEM_PROMPT,
            },
        )
        translated_chunk = _parse_srt_response(response.text, chunk)
        translated_segments.extend(translated_chunk)

        if i < len(chunks) - 1:
            time.sleep(SLEEP_BETWEEN_REQUESTS)

    return translated_segments


def _segments_to_srt(segments: list[dict]) -> str:
    """Converts a list of segments to SRT format string."""
    lines = []
    for i, seg in enumerate(segments, 1):
        start = convert_to_timestamp(seg["start"], "srt")
        end = convert_to_timestamp(seg["end"], "srt")
        lines.append(f"{i}\n{start} --> {end}\n{seg['text'].strip()}\n")
    srt_text = "\n".join(lines)
    return srt_text


def _parse_srt_response(
    response_text: str, original_segments: list[dict]
) -> list[dict]:
    """Parses SRT formatted response back into segments."""
    MIN_SRT_BLOCK_LINES = 3

    translated_segments = []
    blocks = response_text.strip().split("\n\n")

    for block, original in zip(blocks, original_segments, strict=False):
        lines = block.strip().split("\n")
        if len(lines) < MIN_SRT_BLOCK_LINES:
            log.warning("Unexpected SRT block format, using original text.")
            translated_segments.append(original)
            continue

        # lines[0] is entry number, lines[1] is timestamp, lines[2:] is text
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
    prompt_parts = []

    prompt_parts.append(
        f"Translate the following subtitle entries from {source_language} \
        to {target_language}."
    )

    if context_entries:
        prompt_parts.append(
            f"The following {len(context_entries)} entries are provided as context only"
            " to maintain narrative continuity. Do not include them in your translation"
            f" output. Begin your translation from entry {start_entry} only.\n"
        )
        prompt_parts.append("[CONTEXT - DO NOT TRANSLATE]\n")
        prompt_parts.append(_segments_to_srt(context_entries))
        prompt_parts.append("\n[TRANSLATE FROM HERE]\n")

    prompt_parts.append(_segments_to_srt(chunk))
    translation_prompt = "\n".join(prompt_parts)
    return translation_prompt
