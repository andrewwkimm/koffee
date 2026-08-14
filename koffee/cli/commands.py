"""Public CLI commands and registration."""

from koffee.cli.info import info
from koffee.cli.languages import languages
from koffee.cli.main import cli, main
from koffee.cli.subtitles import convert, embed, tracks
from koffee.cli.transcribe import transcribe

__all__ = [
    "cli",
    "convert",
    "embed",
    "info",
    "languages",
    "main",
    "tracks",
    "transcribe",
]
