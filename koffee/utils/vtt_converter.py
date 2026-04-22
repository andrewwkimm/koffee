"""Segments to VTT converter."""

import logging
import uuid
from pathlib import Path

from koffee.utils.timestamp_converter import convert_to_timestamp

log = logging.getLogger(__name__)


def convert_segments_to_vtt(segments: list, output_dir: Path) -> Path:
    """Converts segments to VTT format."""
    log.debug("Converting segments to VTT format.")

    output_file_path = output_dir / f"subtitles_{uuid.uuid4().hex[:8]}.vtt"
    log.debug(f"output_file_path: {output_file_path!r}")

    blocks = []
    for subtitle in segments:
        start = convert_to_timestamp(subtitle["start"], "vtt")
        end = convert_to_timestamp(subtitle["end"], "vtt")
        text = subtitle["text"].strip()
        blocks.append(f"{start} --> {end}\n{text}")

    with Path.open(output_file_path, "w", encoding="utf-8") as file:
        file.write("WEBVTT\n\n" + "\n\n".join(blocks) + "\n")

    return output_file_path
