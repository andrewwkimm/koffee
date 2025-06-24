"""Text to VTT converter."""

import logging
from pathlib import Path

from koffee.utils.timestamp_converter import convert_to_timestamp

log = logging.getLogger(__name__)


def convert_text_to_vtt(transcript: list, output_dir: Path) -> Path:
    """Converts text to VTT format."""
    log.debug("Converting text to VTT format.")

    output_file_path = output_dir / "subtitles.vtt"
    log.debug(f"output_file_path: {repr(output_file_path)}")

    with open(output_file_path, "w", encoding="utf-8") as file:
        file.write("WEBVTT\n\n")

        for idx, subtitle in enumerate(transcript, 1):
            start = convert_to_timestamp(subtitle["start"], "vtt")
            end = convert_to_timestamp(subtitle["end"], "vtt")
            text = subtitle["text"]

            file.write(f"{start} --> {end}\n")
            if idx != len(transcript):
                file.write(f"{text}\n\n")
            else:
                file.write(f"{text}\n")

    log.debug(repr(output_file_path))
    return output_file_path
