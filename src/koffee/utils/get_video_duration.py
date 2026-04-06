"""Utility to get the duration of a video."""

import logging
import subprocess
from pathlib import Path

log = logging.getLogger(__name__)


def get_video_duration(video_file_path: Path | str) -> float:
    """Gets the duration in seconds using ffprobe."""
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(video_file_path),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
    except FileNotFoundError:
        log.error("ffprobe not found. Please install ffmpeg to use this feature.")
        raise

    stdout = result.stdout.strip()
    if not stdout:
        return 0.0

    video_duration = float(stdout)
    return video_duration
