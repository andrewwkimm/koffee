"""Tests for the outputted video files."""

from pathlib import Path

from koffee.utils import get_md5_checksum

api_output = Path("scratch/python_output_video_file.mp4")
cli_output = Path("scratch/cli_output_video_file.mp4")


def test_videos() -> None:
    """Tests if the MD5 checksum is the same across the CLI and Python API outputs."""
    api_output_md5_checksum = get_md5_checksum(api_output)
    cli_output_md5_checksum = get_md5_checksum(cli_output)

    assert api_output_md5_checksum == cli_output_md5_checksum
