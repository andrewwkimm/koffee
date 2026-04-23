"""Subtitle generation, conversion, parsing, and extraction."""

import json
import logging
import re
import subprocess
import uuid
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

from koffee.exceptions import InvalidSubtitleFormatError
from koffee.schemas.types import Segment

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

TIMESTAMP_PATTERN = re.compile(
    r"(\d{2}:\d{2}:\d{2}[,\.]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[,\.]\d{3})"
)

ASS_DIALOGUE_PATTERN = re.compile(
    r"Dialogue:\s*\d+,"
    r"(\d+:\d{2}:\d{2}\.\d{2}),"
    r"(\d+:\d{2}:\d{2}\.\d{2}),"
    r"[^,]*,[^,]*,\d+,\d+,\d+,[^,]*,(.*)"
)


def generate_subtitles(
    subtitle_format: str,
    segments: list[Segment],
    output_dir: Path | None = None,
) -> Path:
    """Generates subtitles from a list of segments."""
    if output_dir is None:
        output_dir = Path.cwd()

    if subtitle_format == "srt":
        subtitle_path = convert_segments_to_srt(segments, output_dir)
    elif subtitle_format == "vtt":
        subtitle_path = convert_segments_to_vtt(segments, output_dir)
    elif subtitle_format == "ass":
        subtitle_path = convert_segments_to_ass(segments, output_dir)
    else:
        error_message = f"Invalid or unsupported subtitle format: {subtitle_format}"
        raise InvalidSubtitleFormatError(error_message)

    return subtitle_path


def convert_segments_to_ass(segments: list[Segment], output_dir: Path) -> Path:
    """Converts segments to ASS format."""
    log.debug("Converting segments to ASS format.")

    output_path = output_dir / f"subtitles_{uuid.uuid4().hex[:8]}.ass"
    log.debug(f"output_path: {output_path!r}")

    with Path.open(output_path, "w", encoding="utf-8") as file:
        file.write(ASS_HEADER)

        for subtitle in segments:
            start = convert_to_timestamp(subtitle["start"], "ass")
            end = convert_to_timestamp(subtitle["end"], "ass")
            text = subtitle["text"].strip().replace("\n", "\\N")
            file.write(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}\n")

    return output_path


def convert_segments_to_srt(segments: list[Segment], output_dir: Path) -> Path:
    """Converts segments to SRT format."""
    log.debug("Converting segments to SRT format.")

    output_path = output_dir / f"subtitles_{uuid.uuid4().hex[:8]}.srt"
    log.debug(f"output_path: {output_path!r}")

    blocks = []
    for idx, subtitle in enumerate(segments, 1):
        start = convert_to_timestamp(subtitle["start"], "srt")
        end = convert_to_timestamp(subtitle["end"], "srt")
        text = subtitle["text"].strip()
        blocks.append(f"{idx}\n{start} --> {end}\n{text}")

    with Path.open(output_path, "w", encoding="utf-8") as file:
        file.write("\n\n".join(blocks) + "\n")

    return output_path


def convert_segments_to_vtt(segments: list[Segment], output_dir: Path) -> Path:
    """Converts segments to VTT format."""
    log.debug("Converting segments to VTT format.")

    output_path = output_dir / f"subtitles_{uuid.uuid4().hex[:8]}.vtt"
    log.debug(f"output_path: {output_path!r}")

    blocks = []
    for subtitle in segments:
        start = convert_to_timestamp(subtitle["start"], "vtt")
        end = convert_to_timestamp(subtitle["end"], "vtt")
        text = subtitle["text"].strip()
        blocks.append(f"{start} --> {end}\n{text}")

    with Path.open(output_path, "w", encoding="utf-8") as file:
        file.write("WEBVTT\n\n" + "\n\n".join(blocks) + "\n")

    return output_path


def convert_to_timestamp(seconds: float | int, subtitle_format: str) -> str:
    """Converts seconds to a subtitle timestamp string."""
    seconds_decimal = Decimal(str(seconds))
    seconds_int = int(seconds_decimal)
    milliseconds = int((seconds_decimal % 1) * 1000)
    ts = timedelta(seconds=seconds_int)
    total_seconds = int(ts.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    if subtitle_format == "srt":
        timestamp = f"{hours:02}:{minutes:02}:{seconds:02},{milliseconds:03}"
    elif subtitle_format == "vtt":
        timestamp = f"{hours:02}:{minutes:02}:{seconds:02}.{milliseconds:03}"
    elif subtitle_format == "ass":
        centiseconds = milliseconds // 10
        timestamp = f"{hours}:{minutes:02}:{seconds:02}.{centiseconds:02}"
    else:
        error_message = f"Invalid or unsupported subtitle format: {subtitle_format}"
        raise InvalidSubtitleFormatError(error_message)

    return timestamp


def extract_subtitle_track(video_path: Path | str, track_index: int = 0) -> Path:
    """Extracts a subtitle track from a video file to a temporary SRT file."""
    output_path = Path(video_path).parent / f".koffee_extracted_{track_index}.srt"

    try:
        subprocess.run(
            [
                "ffmpeg",
                "-i",
                str(video_path),
                "-map",
                f"0:s:{track_index}",
                "-f",
                "srt",
                "-y",
                str(output_path),
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=600,
        )
    except FileNotFoundError:
        log.error("ffmpeg not found. Please install ffmpeg to use this feature.")
        raise
    except subprocess.TimeoutExpired:
        log.error("ffmpeg timed out while extracting subtitle track.")
        raise
    except subprocess.CalledProcessError as error:
        log.error(f"Failed to extract subtitle track: {error.stderr}")
        raise

    return output_path


def get_subtitle_tracks(video_path: Path | str) -> list[dict]:
    """Returns a list of subtitle track metadata from a video file."""
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "s",
                "-show_entries",
                "stream=index:stream_tags=language,title",
                "-of",
                "json",
                str(video_path),
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
    except FileNotFoundError:
        log.error("ffprobe not found. Please install ffmpeg to use this feature.")
        raise
    except subprocess.TimeoutExpired:
        log.error("ffprobe timed out while reading subtitle tracks.")
        raise

    data = json.loads(result.stdout)
    return data.get("streams", [])


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


def _find_timestamp_line(lines: list[str]) -> tuple[int, str, str] | None:
    """Finds the timestamp line in a block and returns (index, start, end)."""
    for i, line in enumerate(lines):
        match = TIMESTAMP_PATTERN.search(line)
        if match:
            return i, match.group(1), match.group(2)
    return None


def _timestamp_to_seconds(timestamp: str) -> float:
    """Converts an SRT/VTT timestamp to seconds."""
    timestamp = timestamp.replace(",", ".")
    hours, minutes, rest = timestamp.split(":")
    seconds, milliseconds = rest.split(".")
    return (
        int(hours) * 3600 + int(minutes) * 60 + int(seconds) + int(milliseconds) / 1000
    )
