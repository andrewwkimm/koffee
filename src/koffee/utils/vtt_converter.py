"""Text to VTT converter."""

import logging
import os
from pathlib import Path
from typing import Optional

from koffee.utils.timestamp_converter import convert_to_timestamp


log = logging.getLogger(__name__)


def convert_text_to_vtt(text: list, output_file_path: Optional[Path] = None) -> Path:
    """Converts translated text to VTT format."""
    log.info("Converting text to VTT format.")

    if output_file_path is None:
        output_file_path = Path(f"{os.getcwd()}/subtitle.vtt")

    with open(output_file_path, "w", encoding="utf-8") as file:
        file.write("WEBVTT\n\n")  # VTT files start with a 'WEBVTT' header

        for idx, subtitle in enumerate(text, 1):
            start = convert_to_timestamp(subtitle["start"], "vtt")
            end = convert_to_timestamp(subtitle["end"], "vtt")
            text = subtitle["text"]

            file.write(f"{start} --> {end}\n")
            if idx != len(text):
                file.write(f"{text}\n\n")
            else:
                file.write(f"{text}\n")

    log.debug(repr(output_file_path))
    return output_file_path
