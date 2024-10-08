"""Text to SRT converter."""

import logging
import os
from pathlib import Path
from typing import Optional

from koffee.utils import convert_to_timestamp


log = logging.getLogger(__name__)


def convert_text_to_srt(
    translated_text: list, output_file_path: Optional[Path] = None
) -> Path:
    """Converts translated text to SRT format."""
    log.info("Converting text to SRT format.")

    if output_file_path is None:
        output_file_path = Path(f"{os.getcwd()}/translated_text.srt")

    with open(output_file_path, "w", encoding="utf-8") as file:
        for idx, subtitle in enumerate(translated_text, 1):
            start = convert_to_timestamp(subtitle["start"])
            end = convert_to_timestamp(subtitle["end"])
            text = subtitle["text"]

            file.write(f"{idx}\n")
            file.write(f"{start} --> {end}\n")
            if idx != len(translated_text):
                file.write(f"{text}\n\n")
            else:
                file.write(f"{text}\n")

    log.debug(repr(output_file_path))
    return output_file_path
