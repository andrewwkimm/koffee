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
        video_file_path,
        config.compute_type,
        config.device,
        config.model,
        config.translation_backend,
    )

    actual: dict = clean_transcript(transcript)

    expected: dict = {
        "segments": [
            {
                "start": 0.0,
                "end": 7.0,
                "text": " When I came out of the tunnel, it was a snowstorm.",
            },
            {
                "start": 7.0,
                "end": 12.0,
                "text": " The bottom of the night became bright.",
            },
            {
                "start": 12.0,
                "end": 16.0,
                "text": " The train stopped in front of the traffic light.",
            },
            {
                "start": 16.0,
                "end": 24.0,
                "text": " A girl approached from the left seat on the other side "
                "and opened the window in front of Shimamura.",
            },
        ],
        "language": "en",
    }

    assert_segments_match(actual["segments"], expected["segments"])
