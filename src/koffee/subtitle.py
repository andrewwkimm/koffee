"""Subtitle generator."""

import os
from pathlib import Path
from typing import Optional

from koffee.utils import convert_text_to_srt, convert_text_to_vtt


def generate_subtitles(
    subtitle_format: str,
    transcript: list,
    output_dir: Optional[Path] = None,
) -> Path:
    """Generates subtitles from a transcript."""
    if output_dir is None:
        output_dir = Path(os.getcwd())

    if subtitle_format == "srt":
        subtitle_file_path = convert_text_to_srt(transcript, output_dir)
    elif subtitle_format == "vtt":
        subtitle_file_path = convert_text_to_vtt(transcript, output_dir)
    else:
        raise ValueError(f"Unsupported subtitle format: {subtitle_format}")

    return subtitle_file_path