"""Tests for ASR."""

import math
from difflib import SequenceMatcher

from koffee.asr import transcribe_text
from koffee.data.config import KoffeeConfig


def assert_segments_match(
    actual: list[dict],
    expected: list[dict],
    text_similarity_threshold: float = 0.90,
    timestamp_tolerance: float = 0.05,
) -> None:
    """Assert that actual and expected segments match within tolerance."""
    assert len(actual) == len(expected), (
        f"Expected {len(expected)} segments, got {len(actual)}"
    )

    for actual_segment, expected_segment in zip(actual, expected, strict=True):
        actual_start = actual_segment["start"]
        actual_end = actual_segment["end"]
        actual_text = actual_segment["text"]
        expected_start = expected_segment["start"]
        expected_end = expected_segment["end"]
        expected_text = expected_segment["text"]

        text_similarity = get_text_similarity(actual_text, expected_text)

        assert math.isclose(actual_start, expected_start, abs_tol=timestamp_tolerance)
        assert math.isclose(actual_end, expected_end, abs_tol=timestamp_tolerance)
        assert text_similarity >= text_similarity_threshold


def clean_transcript(transcript: dict) -> dict:
    """Removes extraneous fields from the transcript."""
    cleaned_segments = [
        {
            "start": segment["start"],
            "end": segment["end"],
            "text": segment["text"],
        }
        for segment in transcript["segments"]
    ]

    cleaned_transcript = {
        "segments": cleaned_segments,
        "language": transcript["language"],
    }
    return cleaned_transcript


def get_text_similarity(actual: str, expected: str) -> float:
    """Calculates the similarity ratio between two texts."""
    text_similarity = SequenceMatcher(None, actual, expected).ratio()
    return text_similarity


def test_transcribe_text() -> None:
    """Tests that ASR successfully transcribes from a video file."""
    video_file_path = "examples/videos/sample_korean_video.mp4"
    config = KoffeeConfig(compute_type="int8")

    transcript = transcribe_text(
        video_file_path, config.compute_type, config.device, config.model
    )

    actual: dict = clean_transcript(transcript)

    expected: dict = {
        "segments": [
            {
                "start": 0.0,
                "end": 6.36,
                "text": " 접경의 긴 터널을 빠져나오면 바로 눈고장이었다.",
            },
            {"start": 7.8, "end": 10.74, "text": " 밤의 밑바닥이 환해졌다."},
            {"start": 12.32, "end": 15.34, "text": " 기차는 신호소 앞에서 멈췄다."},
            {
                "start": 16.98,
                "end": 23.52,
                "text": " 건너편 좌석에서 처녀가 다가와 심화물화 앞 유리창을 열었다.",
            },
        ],
        "language": "ko",
    }

    assert_segments_match(actual["segments"], expected["segments"])
