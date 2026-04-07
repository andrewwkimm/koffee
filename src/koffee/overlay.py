"""Subtitle overlayer."""

import logging
import subprocess
from pathlib import Path

from koffee.exceptions import SubtitleOverlayError

log = logging.getLogger(__name__)


MKV_EXTENSIONS = {".mkv", ".webm"}


def _get_subtitle_codec(output_file_path: Path | str) -> str:
    """Returns the appropriate subtitle codec for the output container."""
    if Path(output_file_path).suffix.lower() in MKV_EXTENSIONS:
        return "srt"
    return "mov_text"


def overlay_subtitles(
    subtitle_file_path: Path | str,
    video_file_path: Path | str,
    output_file_path: Path | str,
    mode: str = "soft",
) -> Path | str:
    """Overlay subtitles to a video file.

    Args:
        subtitle_file_path: Path to the subtitle file.
        video_file_path: Path to the source video file.
        output_file_path: Path for the output video file.
        mode: "soft" for muxed subtitle track, "hard" for burned-in subtitles.
    """
    if mode == "hard":
        return _burn_in_subtitles(subtitle_file_path, video_file_path, output_file_path)
    return _mux_subtitles(subtitle_file_path, video_file_path, output_file_path)


def _mux_subtitles(
    subtitle_file_path: Path | str,
    video_file_path: Path | str,
    output_file_path: Path | str,
) -> Path | str:
    """Muxes subtitles as a soft track (original behavior)."""
    log.info("Overlaying subtitles (soft).")

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
        "language=eng",
        "-y",
        str(output_file_path),
    ]

    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=600)
    except subprocess.CalledProcessError as error:
        raise SubtitleOverlayError(error.stderr) from error

    return output_file_path


def _burn_in_subtitles(
    subtitle_file_path: Path | str,
    video_file_path: Path | str,
    output_file_path: Path | str,
) -> Path | str:
    """Burns subtitles into the video frames (hard subtitles)."""
    log.info("Burning in subtitles (hard).")

    escaped_path = (
        str(subtitle_file_path)
        .replace("\\", "/")
        .replace(":", "\\:")
        .replace("'", "'\\''")
    )

    cmd = [
        "ffmpeg",
        "-i",
        str(video_file_path),
        "-vf",
        f"subtitles='{escaped_path}'",
        "-c:a",
        "copy",
        "-y",
        str(output_file_path),
    ]

    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=600)
    except subprocess.CalledProcessError as error:
        raise SubtitleOverlayError(error.stderr) from error

    return output_file_path
