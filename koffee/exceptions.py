"""Exceptions for koffee."""


class IncompatibleOptionsError(Exception):
    """Config options incompatible with the input file."""


class InvalidSubtitleFormatError(Exception):
    """Subtitle format is invalid or not supported."""


class InvalidVideoFileError(Exception):
    """Video file is invalid or does not exist."""


class MissingDependencyError(Exception):
    """Required external executable not found on PATH."""


class SubtitleEmbedError(Exception):
    """Subtitle embedding not possible for the given file."""


class UnsupportedFileError(Exception):
    """Input file has an unsupported extension."""
