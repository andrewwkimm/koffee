"""Text to ASS converter."""

import logging
import uuid
from pathlib import Path

from koffee.utils.timestamp_converter import convert_to_timestamp

log = logging.getLogger(__name__)

_STYLE_FORMAT = (
    "Format: Name, Fontname, Fontsize, PrimaryColour, "
    "SecondaryColour, OutlineColour, BackColour, Bold, "
    "Italic, Underline, StrikeOut, ScaleX, ScaleY, "
    "Spacing, Angle, BorderStyle, Outline, Shadow, "
    "Alignment, MarginL, MarginR, MarginV, Encoding"
)
_STYLE_DEFAULT = (
    "Style: Default,Arial,48,&H00FFFFFF,&H000000FF,"
    "&H00000000,&H64000000,-1,0,0,0,100,100,0,0,"
    "1,2,1,2,10,10,40,1"
)
_EVENT_FORMAT = (
    "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"
)

ASS_HEADER = (
    "[Script Info]\n"
    "Title: Koffee Subtitles\n"
    "ScriptType: v4.00+\n"
    "PlayResX: 1920\n"
    "PlayResY: 1080\n"
    "\n"
    "[V4+ Styles]\n"
    f"{_STYLE_FORMAT}\n"
    f"{_STYLE_DEFAULT}\n"
    "\n"
    "[Events]\n"
    f"{_EVENT_FORMAT}\n"
)


def convert_text_to_ass(segments: list, output_dir: Path) -> Path:
    """Converts text to ASS format."""
    log.debug("Converting text to ASS format.")

    output_file_path = output_dir / f"subtitles_{uuid.uuid4().hex[:8]}.ass"
    log.debug(f"output_file_path: {output_file_path!r}")

    with Path.open(output_file_path, "w", encoding="utf-8") as file:
        file.write(ASS_HEADER)

        for subtitle in segments:
            start = convert_to_timestamp(subtitle["start"], "ass")
            end = convert_to_timestamp(subtitle["end"], "ass")
            text = subtitle["text"].strip().replace("\n", "\\N")
            file.write(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}\n")

    return output_file_path
