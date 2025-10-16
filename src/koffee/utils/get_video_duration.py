"""Utility to get the duration of a video."""

import subprocess
from pathlib import Path


def get_video_duration(video_file_path: Path | str) -> float:
    """Gets the video duration in seconds using ffmpeg."""
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(video_file_path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    video_duration = float(result.stdout.strip())
    return video_duration
