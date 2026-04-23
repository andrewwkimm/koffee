"""The koffee CLI."""

from koffee.cli.app import app
from koffee.cli.commands import (
    _find_config_path,
    _print_dry_run,
    _resolve_paths,
    _translate_with_progress,
    cli,
    convert,
    embed,
    info,
    languages,
    main,
    tracks,
    transcribe,
)
from koffee.cli.embedded import (
    _handle_embedded_subtitles,
    _select_subtitle_track,
)

__all__ = [
    "_find_config_path",
    "_handle_embedded_subtitles",
    "_print_dry_run",
    "_resolve_paths",
    "_select_subtitle_track",
    "_translate_with_progress",
    "app",
    "cli",
    "convert",
    "embed",
    "info",
    "languages",
    "main",
    "tracks",
    "transcribe",
]
