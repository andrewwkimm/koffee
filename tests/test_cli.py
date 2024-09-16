"""Tests CLI."""

from pathlib import Path

import pytest

from koffee.cli import cli


korean_video_file_name = "translated_korean_file"
korean_video_file_path = Path("examples/videos/sample_korean_video.mp4")

japanese_video_file_name = "translated_japanese_file"
japanese_video_file_path = Path("examples/videos/sample_japanese_video.mp4")


@pytest.mark.parametrize(
    "video_file_path, output_name",
    [
        (korean_video_file_path, korean_video_file_name),
        (japanese_video_file_path, japanese_video_file_name),
    ],
)
def test_cli(video_file_path: Path, output_name: str) -> None:
    """Tests CLI processes a valid video file."""
    file_ext = video_file_path.suffix
    output_directory_path = Path("scratch")

    cli(
        video_file_path,
        output_dir=output_directory_path,
        output_name=output_name,
    )

    output_video_file_path = output_directory_path / (output_name + file_ext)

    assert output_video_file_path.exists()
