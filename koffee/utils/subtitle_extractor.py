"""Embedded subtitle track detection and extraction."""

import json
import logging
import subprocess
from pathlib import Path

log = logging.getLogger(__name__)


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
