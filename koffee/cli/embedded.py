"""Embedded subtitle detection and track selection for the CLI."""

from pathlib import Path

from koffee.cli.app import log
from koffee.schemas.config import KoffeeConfig
from koffee.schemas.domain import SubtitleTrack
from koffee.subtitle import (
    SUBTITLE_EXTENSIONS,
    get_subtitle_tracks,
)


def _handle_embedded_subtitles(video_path: Path, config: KoffeeConfig) -> KoffeeConfig:
    """If the video has embedded subtitles, prompts the user and updates config."""
    tracks = _detect_embedded_subtitles(video_path)
    if not tracks:
        return config

    log.info(f"Found {len(tracks)} embedded subtitle track(s) in {video_path.name}.")
    if not _prompt_use_embedded_subtitles():
        return config

    return _apply_subtitle_track(config, tracks)


def _apply_subtitle_track(
    config: KoffeeConfig, tracks: list[SubtitleTrack]
) -> KoffeeConfig:
    """Selects a subtitle track and returns an updated config."""
    track_index, source_language = _select_subtitle_track(tracks)
    updates = {"use_embedded_subtitles": True, "subtitle_track_index": track_index}
    if source_language:
        updates["source_language"] = source_language

    return config.model_copy(update=updates)


def _select_subtitle_track(
    tracks: list[SubtitleTrack],
) -> tuple[int, str | None]:
    """Returns the selected subtitle-stream ordinal and language."""
    if len(tracks) == 1:
        return 0, tracks[0].language

    log.info("Available subtitle tracks:")
    for position, track in enumerate(tracks):
        language = track.language or "unknown"
        label = f"  [{position}] {language}"
        if track.title:
            label += f" — {track.title}"
        log.info(label)

    user_input = input(f"Select track [0-{len(tracks) - 1}] (default 0): ")
    position = int(user_input.strip()) if user_input.strip().isdigit() else 0
    position = max(0, min(position, len(tracks) - 1))
    return position, tracks[position].language


def _detect_embedded_subtitles(video_path: Path) -> list[SubtitleTrack]:
    """Returns embedded subtitle tracks in the video, or an empty list."""
    if video_path.suffix.lower() in SUBTITLE_EXTENSIONS:
        return []

    return get_subtitle_tracks(video_path)


def _prompt_use_embedded_subtitles() -> bool:
    """Prompts the user to use embedded subtitles instead of running ASR."""
    user_input = input("Translate embedded subtitles instead of running ASR? [Y/n] ")
    return user_input.strip().lower() in ("", "y", "yes")
