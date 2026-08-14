"""Validated immutable models for core subtitle processing."""

import math
from typing import Self

from pydantic import BaseModel, ConfigDict, field_validator, model_validator


class Segment(BaseModel):
    """One validated subtitle segment."""

    model_config = ConfigDict(frozen=True)

    start: float
    end: float
    text: str

    @model_validator(mode="after")
    def _validate_timestamps(self) -> Self:
        """Validates finite, ordered, nonnegative timestamps."""
        if not math.isfinite(self.start) or not math.isfinite(self.end):
            error_message = "Segment timestamps must be finite."
            raise ValueError(error_message)
        if self.start < 0 or self.end < 0:
            error_message = "Segment timestamps must be nonnegative."
            raise ValueError(error_message)
        if self.end < self.start:
            error_message = "Segment end must not precede its start."
            raise ValueError(error_message)
        return self


class Transcript(BaseModel):
    """A validated transcript and its detected source language."""

    model_config = ConfigDict(frozen=True)

    segments: tuple[Segment, ...]
    language: str

    @field_validator("language")
    @classmethod
    def _validate_language(cls, value: str) -> str:
        """Rejects an empty transcript language."""
        normalized = value.strip()
        if not normalized:
            error_message = "Transcript language must not be empty."
            raise ValueError(error_message)
        return normalized


class TranslationChunk(BaseModel):
    """An immutable prompt-ready transcript slice."""

    model_config = ConfigDict(frozen=True)

    segments: tuple[Segment, ...]
    source_language: str
    target_language: str
    start_entry: int

    @field_validator("start_entry")
    @classmethod
    def _validate_start_entry(cls, value: int) -> int:
        """Rejects nonpositive subtitle entry numbers."""
        if value < 1:
            error_message = "Chunk start_entry must be positive."
            raise ValueError(error_message)
        return value


class SubtitleTrack(BaseModel):
    """Validated metadata for one embedded subtitle stream."""

    model_config = ConfigDict(frozen=True)

    index: int
    language: str | None = None
    title: str | None = None

    @field_validator("index")
    @classmethod
    def _validate_index(cls, value: int) -> int:
        """Rejects negative stream indexes."""
        if value < 0:
            error_message = "Subtitle-track index must be nonnegative."
            raise ValueError(error_message)
        return value
