"""Utility to get the duration of a video."""

import subprocess
from pathlib import Path


def get_video_duration(video_file_path: Path | str) -> float:
    """Gets the duration in seconds using ffprobe."""
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

    stdout = result.stdout.strip()
    if not stdout:
        return 0.0

    video_duration = float(stdout)
    return video_duration
