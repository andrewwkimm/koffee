"""Example usage for video translation."""

import koffee


if __name__ == "__main__":
    video_file_path = "examples/videos/sample_korean_video.mp4"
    output_dir = "scratch"
    output_name = "example_video"

    koffee.translate(video_file_path)
