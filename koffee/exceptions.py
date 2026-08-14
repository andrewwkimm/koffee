"""Exceptions for koffee."""

from collections.abc import Sequence

from koffee.schemas.domain import Segment


class KoffeeError(Exception):
    """Base class for all koffee-specific errors."""


class IncompatibleOptionsError(KoffeeError):
    """Config options incompatible with the input file."""


class InvalidSubtitleFormatError(KoffeeError):
    """Subtitle format is invalid or not supported."""


class InvalidVideoFileError(KoffeeError):
    """Video file is invalid or does not exist."""


class MissingApiKeyError(KoffeeError):
    """LLM backend selected without a required API key."""


class MissingDependencyError(KoffeeError):
    """Required external executable not found on PATH."""


class SubtitleEmbedError(KoffeeError):
    """Subtitle embedding not possible for the given file."""


class TranslationPausedError(KoffeeError):
    """Translation paused after durable progress was saved."""


class TranslationIntegrityError(KoffeeError):
    """LLM response does not satisfy the subtitle translation contract."""


class TranslationError(KoffeeError):
    """Translation step failed after successful transcription."""

    def __init__(self, message: str, segments: Sequence[Segment]) -> None:
        """Stores the raw transcript segments alongside the error."""
        super().__init__(message)
        self.segments = tuple(segments)


class UnsupportedFileError(KoffeeError):
    """Input file has an unsupported extension."""
