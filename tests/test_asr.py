"""Tests for ASR."""

from koffee.asr import transcribe_text
from koffee.data.config import koffeeConfig


def clean_transcript(transcript: dict) -> dict:
    """Removes extraneous fields from the transcript."""
    cleaned_segments = [
        {"start": segment["start"], "end": segment["end"], "text": segment["text"]}
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
    config = koffeeConfig()

    transcript = transcribe_text(
        video_file_path, config.compute_type, config.device, config.model
    )

    actual = clean_transcript(transcript)

    expected = {
        "segments": [
            {
                "start": 0.0,
                "end": 6.28,
                "text": " 접경의 긴 터널을 빠져나오면 바로 눈고장이었다.",
            },
            {"start": 7.8, "end": 10.74, "text": " 밤의 밑바닥이 환해졌다."},
            {"start": 12.32, "end": 14.94, "text": " 기차는 신호소 앞에서 멈췄다."},
            {
                "start": 16.98,
                "end": 24.060000000000002,
                "text": " 건너편 좌석에서 처녀가 다가와 심화무라 앞 유리창을 열었다.",
            },
        ],
        "language": "ko",
    }

    assert actual == expected
