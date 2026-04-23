"""Subtitle file parser."""

import logging
import re
from pathlib import Path

from koffee.schemas.types import Segment

log = logging.getLogger(__name__)

TIMESTAMP_PATTERN = re.compile(
    r"(\d{2}:\d{2}:\d{2}[,\.]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[,\.]\d{3})"
)


ASS_DIALOGUE_PATTERN = re.compile(
    r"Dialogue:\s*\d+,"
    r"(\d+:\d{2}:\d{2}\.\d{2}),"
    r"(\d+:\d{2}:\d{2}\.\d{2}),"
    r"[^,]*,[^,]*,\d+,\d+,\d+,[^,]*,(.*)"
)


def parse_subtitle_file(file_path: Path | str) -> list[Segment]:
    """Parses an SRT, VTT, or ASS/SSA file into a list of segment dicts."""
    file_path = Path(file_path)
    text = file_path.read_text(encoding="utf-8")

    if file_path.suffix.lower() in (".ass", ".ssa"):
        return _parse_ass(text, file_path)

    blocks = re.split(r"\n\n+", text.strip())
    segments = []

    for block in blocks:
        lines = block.strip().split("\n")
        match = _find_timestamp_line(lines)
        if match is None:
            continue

        timestamp_idx, start_ts, end_ts = match
        text_lines = lines[timestamp_idx + 1 :]
        if not text_lines:
            continue

        segments.append(
            {
                "start": _timestamp_to_seconds(start_ts),
                "end": _timestamp_to_seconds(end_ts),
                "text": " ".join(line.strip() for line in text_lines),
            }
        )

    log.debug(f"Parsed {len(segments)} segments from {file_path.name}")
    return segments


def _find_timestamp_line(lines: list[str]) -> tuple[int, str, str] | None:
    """Finds the timestamp line in a block and returns (index, start, end)."""
    for i, line in enumerate(lines):
        match = TIMESTAMP_PATTERN.search(line)
        if match:
            return i, match.group(1), match.group(2)
    return None


def _parse_ass(text: str, file_path: Path) -> list[Segment]:
    """Parses ASS/SSA formatted text into segment dicts."""
    segments = []
    for line in text.splitlines():
        match = ASS_DIALOGUE_PATTERN.match(line)
        if not match:
            continue
        start_ts, end_ts, dialogue = match.groups()
        clean_text = re.sub(r"\{[^}]*\}", "", dialogue).strip()
        if not clean_text:
            continue
        segments.append(
            {
                "start": _ass_timestamp_to_seconds(start_ts),
                "end": _ass_timestamp_to_seconds(end_ts),
                "text": clean_text.replace("\\N", " "),
            }
        )

    log.debug(f"Parsed {len(segments)} segments from {file_path.name}")
    return segments


def _ass_timestamp_to_seconds(timestamp: str) -> float:
    """Converts an ASS timestamp (H:MM:SS.cc) to seconds."""
    hours, minutes, rest = timestamp.split(":")
    seconds, centiseconds = rest.split(".")
    return (
        int(hours) * 3600 + int(minutes) * 60 + int(seconds) + int(centiseconds) / 100
    )


def _timestamp_to_seconds(timestamp: str) -> float:
    """Converts an SRT/VTT timestamp to seconds."""
    timestamp = timestamp.replace(",", ".")
    hours, minutes, rest = timestamp.split(":")
    seconds, milliseconds = rest.split(".")
    return (
        int(hours) * 3600 + int(minutes) * 60 + int(seconds) + int(milliseconds) / 1000
    )
