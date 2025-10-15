"""Subtitle overlayer."""

import logging
import subprocess
from pathlib import Path

from koffee.exceptions import SubtitleOverlayError

log = logging.getLogger(__name__)


def overlay_subtitles(
    subtitle_file_path: Path | str,
    video_file_path: Path | str,
    output_file_path: Path | str,
) -> Path | str:
    """Overlay subtitles to a video file."""
    log.info("Overlaying subtitles.")

    cmd = [
        "ffmpeg",
        "-i",
        str(video_file_path),
        "-i",
        str(subtitle_file_path),
        "-c",
        "copy",
        "-c:s",
        "mov_text",
        "-metadata:s:s:0",
        "language=eng",
        "-y",
        str(output_file_path),
    ]

    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as error:
        raise SubtitleOverlayError(error.stderr) from error

    return output_file_path
