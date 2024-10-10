"""Subtitle overlayer."""

import logging
from pathlib import Path
from typing import Union

import ffmpeg

from koffee.exceptions import SubtitleOverlayError


log = logging.getLogger(__name__)


def overlay_subtitles(
    video_file_path: Union[Path, str],
    srt_path: Union[Path, str],
    video_file_output_path: Union[Path, str],
) -> None:
    """Adds subtitles from an SRT file to a video file."""
    # TODO: Investigate why setting output path as a Pathlib
    #       object causes error when the other parameters don't

    log.info("Overlaying subtitles.")

    try:
        ffmpeg.input(video_file_path).output(
            str(video_file_output_path), vf=f"subtitles={srt_path}"
        ).run(overwrite_output=True, capture_stdout=True, capture_stderr=True)
    except Exception as error:
        raise SubtitleOverlayError(error) from error
