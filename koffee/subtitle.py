"""Subtitle generator."""

from pathlib import Path

from koffee.exceptions import InvalidSubtitleFormatError
from koffee.utils import (
    convert_segments_to_ass,
    convert_segments_to_srt,
    convert_segments_to_vtt,
)


def generate_subtitles(
    subtitle_format: str,
    segments: list,
    output_dir: Path | None = None,
) -> Path:
    """Generates subtitles from a list of segments."""
    if output_dir is None:
        output_dir = Path.cwd()

    if subtitle_format == "srt":
        subtitle_file_path = convert_segments_to_srt(segments, output_dir)
    elif subtitle_format == "vtt":
        subtitle_file_path = convert_segments_to_vtt(segments, output_dir)
    elif subtitle_format == "ass":
        subtitle_file_path = convert_segments_to_ass(segments, output_dir)
    else:
        error_message = f"Invalid or unsupported subtitle format: {subtitle_format}"
        raise InvalidSubtitleFormatError(error_message)

    return subtitle_file_path
