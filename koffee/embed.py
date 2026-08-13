"""Subtitle embedding through FFmpeg."""

import logging
import subprocess
from pathlib import Path

from koffee.exceptions import SubtitleEmbedError

log = logging.getLogger(__name__)

EMBED_MODES = frozenset({"soft", "hard"})
SUBTITLE_CODECS = {
    ".mkv": "srt",
    ".webm": "webvtt",
    ".mp4": "mov_text",
    ".m4v": "mov_text",
    ".mov": "mov_text",
}
ISO_639_2_CODE_LENGTH = 3
ISO_639_2_CODES = {
    "ar": "ara",
    "cs": "ces",
    "da": "dan",
    "de": "deu",
    "en": "eng",
    "es": "spa",
    "fi": "fin",
    "fr": "fra",
    "hi": "hin",
    "id": "ind",
    "it": "ita",
    "ja": "jpn",
    "ko": "kor",
    "nl": "nld",
    "no": "nor",
    "pl": "pol",
    "pt": "por",
    "ru": "rus",
    "sv": "swe",
    "th": "tha",
    "tr": "tur",
    "uk": "ukr",
    "vi": "vie",
    "zh": "zho",
}
FFMPEG_TIMEOUT_SECONDS = 600
FFPROBE_TIMEOUT_SECONDS = 30


def embed_subtitles(
    subtitle_path: Path | str,
    video_path: Path | str,
    output_path: Path | str,
    mode: str = "soft",
    language: str = "eng",
) -> Path:
    """Embeds subtitles using a validated embedding mode."""
    if mode not in EMBED_MODES:
        error_message = f"Unsupported subtitle embed mode: {mode!r}."
        raise SubtitleEmbedError(error_message)

    if mode == "hard":
        return _burn_in_subtitles(
            subtitle_path,
            video_path,
            output_path,
        )

    return _mux_subtitles(
        subtitle_path,
        video_path,
        output_path,
        _normalize_language(language),
    )


def _burn_in_subtitles(
    subtitle_path: Path | str,
    video_path: Path | str,
    output_path: Path | str,
) -> Path:
    """Burns subtitles into the primary video stream."""
    log.info("Burning in subtitles (hard).")

    if not _ffmpeg_supports_subtitles_filter():
        error_message = (
            "Hard subtitle burn-in requires an ffmpeg built with libass. "
            "On macOS, install it with `brew install ffmpeg-full`."
        )
        raise SubtitleEmbedError(error_message)

    command = [
        "ffmpeg",
        "-i",
        str(video_path),
        "-map",
        "0",
        "-map_metadata",
        "0",
        "-map_chapters",
        "0",
        "-vf",
        f"subtitles={_escape_subtitle_filter_path(subtitle_path)}",
        "-c",
        "copy",
        "-c:v:0",
        "libx264",
        "-y",
        str(output_path),
    ]
    _run_ffmpeg(command, "burning in subtitles")
    return Path(output_path)


def _ffmpeg_supports_subtitles_filter() -> bool:
    """Returns whether FFmpeg provides the libass subtitle filter."""
    result = subprocess.run(
        ["ffmpeg", "-hide_banner", "-filters"],
        capture_output=True,
        text=True,
        check=False,
    )
    return "subtitles" in result.stdout


def _escape_subtitle_filter_path(
    subtitle_path: Path | str,
) -> str:
    """Escapes a path for the FFmpeg subtitle filter."""
    escaped_path = str(subtitle_path).replace("\\", "/")
    for character in (":", "'", "[", "]", ",", ";"):
        escaped_path = escaped_path.replace(
            character,
            f"\\{character}",
        )
    return escaped_path


def _mux_subtitles(
    subtitle_path: Path | str,
    video_path: Path | str,
    output_path: Path | str,
    language: str,
) -> Path:
    """Adds one subtitle while copying every source stream."""
    log.info("Embedding subtitles (soft).")

    subtitle_index = _count_subtitle_streams(video_path)
    subtitle_codec = _subtitle_codec(Path(output_path).suffix)
    subtitle_stream = f"s:{subtitle_index}"
    command = [
        "ffmpeg",
        "-i",
        str(video_path),
        "-i",
        str(subtitle_path),
        "-map",
        "0",
        "-map",
        "1:0",
        "-map_metadata",
        "0",
        "-map_chapters",
        "0",
        "-c",
        "copy",
        f"-c:{subtitle_stream}",
        subtitle_codec,
        f"-metadata:s:{subtitle_stream}",
        f"language={language}",
        "-y",
        str(output_path),
    ]
    _run_ffmpeg(command, "muxing subtitles")
    return Path(output_path)


def _count_subtitle_streams(
    video_path: Path | str,
) -> int:
    """Returns the number of existing subtitle streams."""
    command = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "s",
        "-show_entries",
        "stream=index",
        "-of",
        "csv=p=0",
        str(video_path),
    ]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
            timeout=FFPROBE_TIMEOUT_SECONDS,
        )
    except FileNotFoundError:
        log.error("ffprobe not found. Install ffmpeg to use this feature.")
        raise
    except subprocess.TimeoutExpired:
        log.error("ffprobe timed out while reading subtitle streams.")
        raise
    except subprocess.CalledProcessError as error:
        raise SubtitleEmbedError(error.stderr or str(error)) from error

    return len([line for line in result.stdout.splitlines() if line.strip()])


def _subtitle_codec(output_suffix: str) -> str:
    """Returns the subtitle codec required by the container."""
    codec = SUBTITLE_CODECS.get(output_suffix.lower())
    if codec is None:
        error_message = f"Unsupported video container for subtitles: {output_suffix!r}."
        raise SubtitleEmbedError(error_message)
    return codec


def _normalize_language(language: str) -> str:
    """Returns an ISO 639-2 metadata code or ``und``."""
    normalized = language.strip().lower()
    if len(normalized) == ISO_639_2_CODE_LENGTH:
        return normalized
    return ISO_639_2_CODES.get(normalized, "und")


def _run_ffmpeg(
    command: list[str],
    operation: str,
) -> None:
    """Runs FFmpeg and translates process failures."""
    try:
        subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
            timeout=FFMPEG_TIMEOUT_SECONDS,
        )
    except FileNotFoundError:
        log.error("ffmpeg not found. Install ffmpeg to use this feature.")
        raise
    except subprocess.TimeoutExpired:
        log.error("ffmpeg timed out while %s.", operation)
        raise
    except subprocess.CalledProcessError as error:
        raise SubtitleEmbedError(error.stderr) from error
