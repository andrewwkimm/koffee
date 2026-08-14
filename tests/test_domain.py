"""Tests for validated subtitle domain models."""

import math

import pytest
from pydantic import ValidationError

from koffee.schemas.domain import (
    Segment,
    SubtitleTrack,
    Transcript,
    TranslationChunk,
)


def test_transcript_converts_segments_to_frozen_models() -> None:
    """Tests validation of mapping data at the domain boundary."""
    transcript = Transcript.model_validate(
        {
            "segments": [
                {
                    "start": 0.0,
                    "end": 1.5,
                    "text": "Hello.",
                }
            ],
            "language": "ja",
        }
    )

    expected_segment_count = 1
    assert len(transcript.segments) == expected_segment_count
    assert transcript.segments[0].text == "Hello."


@pytest.mark.parametrize(
    ("start", "end", "message"),
    [
        (-1.0, 1.0, "nonnegative"),
        (2.0, 1.0, "must not precede"),
        (math.inf, math.inf, "finite"),
    ],
)
def test_segment_rejects_invalid_timestamps(
    start: float,
    end: float,
    message: str,
) -> None:
    """Tests timestamp invariants."""
    with pytest.raises(ValidationError, match=message):
        Segment(start=start, end=end, text="Invalid")


def test_translation_chunk_requires_positive_start_entry() -> None:
    """Tests rejection of invalid global entry numbers."""
    with pytest.raises(ValidationError, match="positive"):
        TranslationChunk(
            segments=(),
            source_language="ja",
            target_language="en",
            start_entry=0,
        )


def test_subtitle_track_rejects_negative_index() -> None:
    """Tests rejection of negative stream indexes."""
    with pytest.raises(ValidationError, match="nonnegative"):
        SubtitleTrack(index=-1)


def test_transcript_rejects_empty_language() -> None:
    """Tests rejection of empty transcript language."""
    with pytest.raises(ValidationError, match="must not be empty"):
        Transcript(segments=(), language=" ")
