"""Text to SRT converter."""

import logging
import uuid
from pathlib import Path

from koffee.utils.timestamp_converter import convert_to_timestamp

log = logging.getLogger(__name__)


def convert_text_to_srt(segments: list, output_dir: Path) -> Path:
    """Converts text to SRT format."""
    log.debug("Converting text to SRT format.")

    output_file_path = output_dir / f"subtitles_{uuid.uuid4().hex[:8]}.srt"
    log.debug(f"output_file_path: {output_file_path!r}")

    blocks = []
    for idx, subtitle in enumerate(segments, 1):
        start = convert_to_timestamp(subtitle["start"], "srt")
        end = convert_to_timestamp(subtitle["end"], "srt")
        text = subtitle["text"].strip()
        blocks.append(f"{idx}\n{start} --> {end}\n{text}")

    with Path.open(output_file_path, "w", encoding="utf-8") as file:
        file.write("\n\n".join(blocks) + "\n")

    return output_file_path
