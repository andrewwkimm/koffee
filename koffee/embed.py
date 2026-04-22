"""Subtitle embedder."""

import logging
import subprocess
from pathlib import Path

from koffee.exceptions import SubtitleEmbedError

log = logging.getLogger(__name__)


MKV_EXTENSIONS = {".mkv", ".webm"}


def _get_subtitle_codec(output_file_path: Path | str) -> str:
    """Returns the appropriate subtitle codec for the output container."""
    if Path(output_file_path).suffix.lower() in MKV_EXTENSIONS:
        return "srt"
    return "mov_text"


def embed_subtitles(
    subtitle_file_path: Path | str,
    video_file_path: Path | str,
    output_file_path: Path | str,
    mode: str = "soft",
    language: str = "eng",
) -> Path | str:
    """Embeds subtitles into a video file.

    Args:
        subtitle_file_path: Path to the subtitle file.
        video_file_path: Path to the source video file.
        output_file_path: Path for the output video file.
        mode: "soft" for muxed subtitle track, "hard" for burned-in subtitles.
        language: ISO 639-2 language code for the subtitle metadata.
    """
    if mode == "hard":
        return _burn_in_subtitles(subtitle_file_path, video_file_path, output_file_path)
    return _mux_subtitles(
        subtitle_file_path, video_file_path, output_file_path, language
    )


def _mux_subtitles(
    subtitle_file_path: Path | str,
    video_file_path: Path | str,
    output_file_path: Path | str,
    language: str = "eng",
) -> Path | str:
    """Muxes subtitles as a soft track (original behavior)."""
    log.info("Embedding subtitles (soft).")

    subtitle_codec = _get_subtitle_codec(output_file_path)

    cmd = [
        "ffmpeg",
        "-i",
        str(video_file_path),
        "-i",
        str(subtitle_file_path),
        "-c",
        "copy",
        "-c:s",
        subtitle_codec,
        "-metadata:s:s:0",
        f"language={language}",
        "-y",
        str(output_file_path),
    ]

    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=600)
    except FileNotFoundError:
        log.error("ffmpeg not found. Please install ffmpeg to use this feature.")
        raise
    except subprocess.TimeoutExpired:
        log.error("ffmpeg timed out while muxing subtitles.")
        raise
    except subprocess.CalledProcessError as error:
        raise SubtitleEmbedError(error.stderr) from error

    return output_file_path


def _escape_subtitle_filter_path(subtitle_file_path: Path | str) -> str:
    """Escapes a path for use in the ffmpeg `subtitles=` filter argument."""
    path = str(subtitle_file_path).replace("\\", "/")
    for char in (":", "'", "[", "]", ",", ";"):
        path = path.replace(char, f"\\{char}")
    return path


def _burn_in_subtitles(
    subtitle_file_path: Path | str,
    video_file_path: Path | str,
    output_file_path: Path | str,
) -> Path | str:
    """Burns subtitles into the video frames (hard subtitles)."""
    log.info("Burning in subtitles (hard).")

    escaped_path = _escape_subtitle_filter_path(subtitle_file_path)

    cmd = [
        "ffmpeg",
        "-i",
        str(video_file_path),
        "-vf",
        f"subtitles={escaped_path}",
        "-c:a",
        "copy",
        "-y",
        str(output_file_path),
    ]

    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=600)
    except FileNotFoundError:
        log.error("ffmpeg not found. Please install ffmpeg to use this feature.")
        raise
    except subprocess.TimeoutExpired:
        log.error("ffmpeg timed out while burning in subtitles.")
        raise
    except subprocess.CalledProcessError as error:
        raise SubtitleEmbedError(error.stderr) from error

    return output_file_path
