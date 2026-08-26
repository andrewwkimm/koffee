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
from koffee.schemas.domain import Segment, SubtitleTrack

log = logging.getLogger(__name__)

SUBTITLE_EXTENSIONS = frozenset({".ass", ".srt", ".ssa", ".vtt"})
BITMAP_SUBTITLE_CODECS = frozenset(
    {"dvb_subtitle", "dvd_subtitle", "hdmv_pgs_subtitle", "xsub"}
)
FFMPEG_TIMEOUT_SECONDS = 600
FFPROBE_TIMEOUT_SECONDS = 30

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
    r"((?:\d{2}:)?\d{2}:\d{2}[,.]\d{3})\s*-->\s*"
    r"((?:\d{2}:)?\d{2}:\d{2}[,.]\d{3})"
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
            start = convert_to_timestamp(subtitle.start, "ass")
            end = convert_to_timestamp(subtitle.end, "ass")
            text = subtitle.text.strip().replace("\n", "\\N")
            file.write(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}\n")

    return output_path


def convert_segments_to_srt(segments: list[Segment], output_dir: Path) -> Path:
    """Converts segments to SRT format."""
    log.debug("Converting segments to SRT format.")

    output_path = output_dir / f"subtitles_{uuid.uuid4().hex[:8]}.srt"
    log.debug(f"output_path: {output_path!r}")

    blocks = []
    for idx, subtitle in enumerate(segments, 1):
        start = convert_to_timestamp(subtitle.start, "srt")
        end = convert_to_timestamp(subtitle.end, "srt")
        text = subtitle.text.strip()
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
        start = convert_to_timestamp(subtitle.start, "vtt")
        end = convert_to_timestamp(subtitle.end, "vtt")
        text = subtitle.text.strip()
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


def extract_subtitle_track(
    video_path: Path | str,
    subtitle_ordinal: int = 0,
    output_dir: Path | None = None,
    *,
    track_index: int | None = None,
) -> Path:
    """Extracts a subtitle track into the caller-owned directory."""
    if track_index is not None:
        if subtitle_ordinal != 0:
            error_message = (
                "subtitle_ordinal and legacy track_index cannot both select "
                "a subtitle track."
            )
            raise ValueError(error_message)
        subtitle_ordinal = track_index

    destination = output_dir if output_dir is not None else Path(video_path).parent
    destination.mkdir(parents=True, exist_ok=True)
    output_path = destination / f"embedded_subtitle_{subtitle_ordinal}.srt"

    try:
        subprocess.run(
            [
                "ffmpeg",
                "-i",
                str(video_path),
                "-map",
                f"0:s:{subtitle_ordinal}",
                "-f",
                "srt",
                "-y",
                str(output_path),
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=FFMPEG_TIMEOUT_SECONDS,
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


def get_subtitle_tracks(
    video_path: Path | str,
) -> list[SubtitleTrack]:
    """Returns validated subtitle-track metadata."""
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "s",
                "-show_entries",
                "stream=index,codec_name:stream_tags=language,title",
                "-of",
                "json",
                str(video_path),
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=FFPROBE_TIMEOUT_SECONDS,
        )
    except FileNotFoundError:
        log.error("ffprobe not found. Please install ffmpeg to use this feature.")
        raise
    except subprocess.TimeoutExpired:
        log.error("ffprobe timed out while reading subtitle tracks.")
        raise

    streams = json.loads(result.stdout).get("streams", [])
    return [
        SubtitleTrack(
            absolute_stream_index=stream["index"],
            subtitle_ordinal=subtitle_ordinal,
            codec_name=stream["codec_name"],
            language=stream.get("tags", {}).get("language"),
            title=stream.get("tags", {}).get("title"),
        )
        for subtitle_ordinal, stream in enumerate(streams)
        if stream["codec_name"] not in BITMAP_SUBTITLE_CODECS
    ]


def parse_subtitle_file(
    file_path: Path | str,
) -> list[Segment]:
    """Parses supported subtitles and rejects empty or malformed content."""
    subtitle_path = Path(file_path)
    text = subtitle_path.read_text(encoding="utf-8")
    if not text.strip():
        raise InvalidSubtitleFormatError(
            f"Subtitle file {subtitle_path.name} is empty or whitespace-only."
        )

    suffix = subtitle_path.suffix.lower()
    if suffix in (".ass", ".ssa"):
        segments = _parse_ass(text, subtitle_path)
    elif suffix == ".vtt":
        segments = _parse_srt_or_vtt(text, subtitle_path, is_vtt=True)
    else:
        segments = _parse_srt_or_vtt(text, subtitle_path, is_vtt=False)

    if not segments:
        raise InvalidSubtitleFormatError(
            f"No valid subtitle cues found in {subtitle_path.name}."
        )
    log.debug(f"Parsed {len(segments)} segments from {subtitle_path.name}")
    return segments


def _parse_srt_or_vtt(text: str, file_path: Path, *, is_vtt: bool) -> list[Segment]:
    """Returns cues only when every cue-like block is valid."""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").lstrip("\ufeff")
    blocks = list(re.split(r"\n[ \t]*\n+", normalized.strip()))
    segments = []
    for block_number, block in enumerate(blocks, 1):
        lines = block.splitlines()
        if is_vtt and _is_vtt_metadata_block(lines, block_number):
            continue
        timestamp_index = 1 if len(lines) > 1 and "-->" not in lines[0] else 0
        if timestamp_index >= len(lines) or "-->" not in lines[timestamp_index]:
            raise _subtitle_block_error(file_path, block_number, "missing timestamp")
        timestamp_line = lines[timestamp_index].strip()
        match = TIMESTAMP_PATTERN.match(timestamp_line)
        valid_suffix = timestamp_line[match.end() :] if match is not None else ""
        has_invalid_suffix = (
            bool(valid_suffix.strip())
            if not is_vtt
            else bool(valid_suffix) and not valid_suffix.startswith(" ")
        )
        if match is None or has_invalid_suffix:
            raise _subtitle_block_error(file_path, block_number, "malformed timestamp")
        text_lines = [
            line.strip() for line in lines[timestamp_index + 1 :] if line.strip()
        ]
        if not text_lines:
            raise _subtitle_block_error(file_path, block_number, "missing cue text")
        try:
            segment = Segment(
                start=_timestamp_to_seconds(match.group(1)),
                end=_timestamp_to_seconds(match.group(2)),
                text=" ".join(text_lines),
            )
        except (ValueError, TypeError) as error:
            raise _subtitle_block_error(
                file_path, block_number, "invalid timestamp values"
            ) from error
        segments.append(segment)
    return segments


def _is_vtt_metadata_block(lines: list[str], block_number: int) -> bool:
    """Returns whether a block is valid preserved WebVTT metadata."""
    first = lines[0].strip()
    if block_number == 1 and first.startswith("WEBVTT"):
        return True
    if first in {"STYLE", "REGION"}:
        return True
    return first == "NOTE" or first.startswith("NOTE ")


def _subtitle_block_error(
    file_path: Path, block_number: int, problem: str
) -> InvalidSubtitleFormatError:
    """Returns a contextual whole-file parse failure."""
    return InvalidSubtitleFormatError(
        f"Malformed subtitle cue in {file_path.name}, block {block_number}: {problem}."
    )


def _parse_ass(text: str, file_path: Path) -> list[Segment]:
    """Returns ASS/SSA cues only when every dialogue line is valid."""
    segments = []
    for line_number, line in enumerate(text.splitlines(), 1):
        if not line.lstrip().startswith("Dialogue:"):
            continue
        match = ASS_DIALOGUE_PATTERN.fullmatch(line)
        if match is None:
            raise InvalidSubtitleFormatError(
                f"Malformed ASS dialogue in {file_path.name}, line {line_number}."
            )
        start_timestamp, end_timestamp, dialogue = match.groups()
        clean_text = re.sub(r"\{[^}]*\}", "", dialogue).strip()
        if not clean_text:
            raise InvalidSubtitleFormatError(
                f"Malformed ASS dialogue in {file_path.name}, line {line_number}: "
                "missing cue text."
            )
        try:
            segment = Segment(
                start=_ass_timestamp_to_seconds(start_timestamp),
                end=_ass_timestamp_to_seconds(end_timestamp),
                text=clean_text.replace("\\N", " "),
            )
        except (ValueError, TypeError) as error:
            raise InvalidSubtitleFormatError(
                f"Malformed ASS dialogue in {file_path.name}, line {line_number}: "
                "invalid timestamp values."
            ) from error
        segments.append(segment)
    return segments


def _ass_timestamp_to_seconds(timestamp: str) -> float:
    """Converts an ASS timestamp (H:MM:SS.cc) to seconds."""
    hours, minutes, rest = timestamp.split(":")
    seconds, centiseconds = rest.split(".")
    return (
        int(hours) * 3600 + int(minutes) * 60 + int(seconds) + int(centiseconds) / 100
    )


def _timestamp_to_seconds(timestamp: str) -> float:
    """Converts an SRT or WebVTT timestamp to seconds."""
    fields = timestamp.replace(",", ".").split(":")
    match fields:
        case [minutes, remainder]:
            hours = "0"
        case [hours, minutes, remainder]:
            pass
        case _:
            error_message = f"Invalid subtitle timestamp: {timestamp!r}."
            raise InvalidSubtitleFormatError(error_message)

    seconds, milliseconds = remainder.split(".")
    return (
        int(hours) * 3600 + int(minutes) * 60 + int(seconds) + int(milliseconds) / 1000
    )


def segments_to_srt(segments: list[Segment], start_entry: int = 1) -> str:
    """Converts segments to SRT text beginning at the requested entry number."""
    lines = []
    for entry_number, segment in enumerate(segments, start_entry):
        start = convert_to_timestamp(segment.start, "srt")
        end = convert_to_timestamp(segment.end, "srt")
        text = segment.text.strip()
        lines.append(f"{entry_number}\n{start} --> {end}\n{text}\n")

    srt_text = "\n".join(lines)
    return srt_text
