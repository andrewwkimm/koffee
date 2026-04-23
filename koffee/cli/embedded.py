"""Embedded subtitle detection and track selection for the CLI."""

from pathlib import Path

from koffee.api import SUBTITLE_EXTENSIONS
from koffee.cli.app import log
from koffee.schemas.config import KoffeeConfig
from koffee.subtitle import get_subtitle_tracks


def _handle_embedded_subtitles(video_path: Path, config: KoffeeConfig) -> KoffeeConfig:
    """If the video has embedded subtitles, prompts the user and updates config."""
    tracks = _detect_embedded_subtitles(video_path)
    if not tracks:
        return config

    log.info(f"Found {len(tracks)} embedded subtitle track(s) in {video_path.name}.")
    if not _prompt_use_embedded_subtitles():
        return config

    return _apply_subtitle_track(config, tracks)


def _apply_subtitle_track(config: KoffeeConfig, tracks: list[dict]) -> KoffeeConfig:
    """Selects a subtitle track and returns an updated config."""
    track_index, source_language = _select_subtitle_track(tracks)
    updates = {"use_embedded_subtitles": True, "subtitle_track_index": track_index}
    if source_language:
        updates["source_language"] = source_language

    return config.model_copy(update=updates)


def _select_subtitle_track(tracks: list[dict]) -> tuple[int, str | None]:
    """Prompts user to select a subtitle track if multiple are available."""
    if len(tracks) == 1:
        language = tracks[0].get("tags", {}).get("language")
        return 0, language

    log.info("Available subtitle tracks:")
    for i, track in enumerate(tracks):
        tags = track.get("tags", {})
        language = tags.get("language", "unknown")
        title = tags.get("title", "")
        label = f"  [{i}] {language}"
        if title:
            label += f" — {title}"
        log.info(label)

    user_input = input(f"Select track [0-{len(tracks) - 1}] (default 0): ")
    index = int(user_input.strip()) if user_input.strip().isdigit() else 0
    index = max(0, min(index, len(tracks) - 1))

    language = tracks[index].get("tags", {}).get("language")
    return index, language


def _detect_embedded_subtitles(video_path: Path) -> list[dict]:
    """Returns embedded subtitle tracks in the video, or an empty list."""
    if video_path.suffix.lower() in SUBTITLE_EXTENSIONS:
        return []

    return get_subtitle_tracks(video_path)


def _prompt_use_embedded_subtitles() -> bool:
    """Prompts the user to use embedded subtitles instead of running ASR."""
    user_input = input("Translate embedded subtitles instead of running ASR? [Y/n] ")
    return user_input.strip().lower() in ("", "y", "yes")
