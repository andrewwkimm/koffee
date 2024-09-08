"""Subtitle overlayer."""

from pathlib import Path
from typing import Union

import ffmpeg


def overlay_subtitles(
    video_file_path: Union[Path, str],
    srt_path: Union[Path, str],
    video_file_output_path: Union[Path, str],
) -> None:
    """Adds subtitles from an SRT file to a video file."""
    # TODO: Investigate why setting output path as a Pathlib
    #       object causes error when the other parameters don't

    ffmpeg.input(video_file_path).output(
        str(video_file_output_path), vf=f"subtitles={srt_path}"
    ).run(overwrite_output=True)
