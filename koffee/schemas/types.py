"""Type definitions for transcript, segment, and chunk shapes."""

from typing import TypedDict


class Segment(TypedDict):
    """A single subtitle segment with timing and text."""

    start: float
    end: float
    text: str


class Transcript(TypedDict):
    """A transcript produced by ASR or parsed from a subtitle file."""

    segments: list[Segment]
    language: str


class Chunk(TypedDict):
    """A prompt-ready slice of a transcript for a single LLM call."""

    chunk: list[Segment]
    source_language: str
    target_language: str
    start_entry: int
