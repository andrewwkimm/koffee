"""Tests for ASR."""

import math
from typing import Any, cast

from koffee.asr import transcribe_text
from koffee.data.config import KoffeeConfig


def clean_transcript(transcript: dict) -> dict:
    """Removes extraneous fields from the transcript."""
    cleaned_segments = [
        {
            "start": segment["start"],
            "end": segment["end"],
            "text": segment["text"].strip(),
        }
        for segment in transcript["segments"]
    ]

    cleaned_transcript = {
        "segments": cleaned_segments,
        "language": transcript["language"],
    }
    return cleaned_transcript


def test_transcribe_text() -> None:
    """Tests that ASR successfully transcribes from a video file."""
    video_file_path = "examples/videos/sample_korean_video.mp4"
    config = KoffeeConfig(compute_type="int8")

    transcript = transcribe_text(
        video_file_path, config.compute_type, config.device, config.model
    )

    actual = clean_transcript(transcript)

    expected = {
        "segments": [
            {
                "start": 0.0,
                "end": 6.36,
                "text": "접경의 긴 터널을 빠져나오면 바로 눈고장이었다.",
            },
            {"start": 7.8, "end": 10.74, "text": " 밤의 밑바닥이 환해졌다."},
            {"start": 12.32, "end": 15.34, "text": " 기차는 신호소 앞에서 멈췄다."},
            {
                "start": 16.98,
                "end": 23.52,
                "text": "건너편 좌석에서 처녀가 다가와 심화물화 앞 유리창을 열었다.",
            },
        ],
        "language": "ko",
    }

    actual_segments = cast(list[dict[str, Any]], actual["segments"].strip())
    expected_segments = cast(list[dict[str, Any]], expected["segments"].strip())

    assert len(actual_segments) == len(expected_segments)

    for actual_segment, expected_segment in zip(
        actual_segments, expected_segments, strict=True
    ):
        assert math.isclose(
            actual_segment["start"], expected_segment["start"], abs_tol=0.05
        )
        assert math.isclose(
            actual_segment["end"], expected_segment["end"], abs_tol=0.05
        )
        assert actual_segment["text"] == expected_segment["text"]
