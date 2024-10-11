"""Subtitle overlayer."""

import logging
from pathlib import Path
from typing import Union

import ffmpeg

from koffee.exceptions import SubtitleOverlayError


log = logging.getLogger(__name__)


def overlay_subtitles(
    subtitle_file_path: Union[Path, str],
    video_file_path: Union[Path, str],
    output_file_path: Union[Path, str],
) -> Union[Path, str]:
    """Overlay subtitles to a video file."""
    log.info("Overlaying subtitles.")

    try:
        ffmpeg.input(video_file_path).output(
            str(output_file_path), vf=f"subtitles={subtitle_file_path}"
        ).run(overwrite_output=True, capture_stdout=True, capture_stderr=True)
    except Exception as error:
        error_message = f"Subtitle overlaying failed: {error}"
        raise SubtitleOverlayError(error_message) from error

    return output_file_path
