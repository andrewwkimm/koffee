"""Subtitle embedder."""

import logging
import subprocess
from pathlib import Path

from koffee.exceptions import SubtitleEmbedError

log = logging.getLogger(__name__)


MKV_EXTENSIONS = {".mkv", ".webm"}


def embed_subtitles(
    subtitle_path: Path | str,
    video_path: Path | str,
    output_path: Path | str,
    mode: str = "soft",
    language: str = "eng",
) -> Path | str:
    """Embeds subtitles into a video file.

    Args:
        subtitle_path: Path to the subtitle file.
        video_path: Path to the source video file.
        output_path: Path for the output video file.
        mode: "soft" for muxed subtitle track, "hard" for burned-in subtitles.
        language: ISO 639-2 language code for the subtitle metadata.
    """
    if mode == "hard":
        return _burn_in_subtitles(subtitle_path, video_path, output_path)
    return _mux_subtitles(subtitle_path, video_path, output_path, language)


def _burn_in_subtitles(
    subtitle_path: Path | str,
    video_path: Path | str,
    output_path: Path | str,
) -> Path | str:
    """Burns subtitles into the video frames (hard subtitles)."""
    log.info("Burning in subtitles (hard).")

    escaped_path = _escape_subtitle_filter_path(subtitle_path)

    cmd = [
        "ffmpeg",
        "-i",
        str(video_path),
        "-vf",
        f"subtitles={escaped_path}",
        "-c:a",
        "copy",
        "-y",
        str(output_path),
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

    return output_path


def _escape_subtitle_filter_path(subtitle_path: Path | str) -> str:
    """Escapes a path for use in the ffmpeg `subtitles=` filter argument."""
    path = str(subtitle_path).replace("\\", "/")
    for char in (":", "'", "[", "]", ",", ";"):
        path = path.replace(char, f"\\{char}")
    return path


def _mux_subtitles(
    subtitle_path: Path | str,
    video_path: Path | str,
    output_path: Path | str,
    language: str = "eng",
) -> Path | str:
    """Muxes subtitles as a soft track (original behavior)."""
    log.info("Embedding subtitles (soft).")

    if Path(output_path).suffix.lower() in MKV_EXTENSIONS:
        subtitle_codec = "srt"
    else:
        subtitle_codec = "mov_text"

    cmd = [
        "ffmpeg",
        "-i",
        str(video_path),
        "-i",
        str(subtitle_path),
        "-c",
        "copy",
        "-c:s",
        subtitle_codec,
        "-metadata:s:s:0",
        f"language={language}",
        "-y",
        str(output_path),
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

    return output_path
