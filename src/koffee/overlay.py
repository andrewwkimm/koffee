"""Subtitle overlayer."""

import logging
from pathlib import Path

import ffmpeg

from koffee.exceptions import SubtitleOverlayError

log = logging.getLogger(__name__)


def overlay_subtitles(
    subtitle_file_path: Path | str,
    video_file_path: Path | str,
    output_file_path: Path | str,
) -> Path | str:
    """Overlay subtitles to a video file."""
    log.info("Overlaying subtitles.")

    try:
        ffmpeg.input(video_file_path).output(
            str(output_file_path), vf=f"subtitles={subtitle_file_path}"
        ).run(overwrite_output=True, capture_stdout=True, capture_stderr=True)
    except ffmpeg.Error as error:
        error_message = error.stderr.decode("utf-8")
        raise SubtitleOverlayError(error_message) from error

    return output_file_path
