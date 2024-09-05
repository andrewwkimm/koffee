"""Utility to convert JSON to SRT."""

from datetime import timedelta
from pathlib import Path
from typing import Optional, Union


def convert_json_to_srt(
    translated_text: list, output_file_path: Optional[Union[Path, str]] = None
) -> Path:
    """Converts translated JSON to SRT."""
    if output_file_path is None:
        output_file_path = Path("scratch/tmp/translated_text.srt")

    with open(output_file_path, "w", encoding="utf-8") as file:
        for idx, subtitle in enumerate(translated_text, 1):
            start = format_timestamp(subtitle["start"])
            end = format_timestamp(subtitle["end"])
            text = subtitle["text"]

            file.write(f"{idx}\n")
            file.write(f"{start} --> {end}\n")
            file.write(f"{text}\n\n")

    return output_file_path


def format_timestamp(seconds: float) -> str:
    """Converts seconds to SRT timestamp format."""
    ms = int((seconds % 1) * 1000)
    ts = timedelta(seconds=int(seconds))
    return f"{str(ts)},{ms:03}"
