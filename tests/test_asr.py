"""Tests ASR."""

from pathlib import Path

from koffee.asr import transcribe_text


def remove_word_segments(transcript: dict) -> dict:
    """Removes word segments from transcript."""
    cleaned_transcript = {
        "segments": [
            {
                key: value
                for key, value in segment.items()
                if key not in {"word_segments", "words"}
            }
            for segment in transcript.get("segments", [])
        ],
        "language": transcript.get("language", ""),
    }
    return cleaned_transcript


def test_transcribe_text() -> None:
    """Tests that ASR successfully transcribes from a video file."""
    video_file_path = Path("examples/videos/sample_korean_video.mp4")
    transcript = transcribe_text(video_file_path, 16, "float32", "cpu", "large-v3")

    actual = remove_word_segments(transcript)

    expected = {
        "segments": [
            {
                "start": 0.009,
                "end": 3.535,
                "text": " 국경의 긴 터널을 빠져나오자 설국이었다.",
            },
            {"start": 4.015, "end": 5.558, "text": "밤의 밑바닥이 하얘졌다."},
            {"start": 5.938, "end": 7.721, "text": "신호소에 기차가 멈춰 섰다."},
            {
                "start": 8.042,
                "end": 13.11,
                "text": "건너편 좌석의 여자가 일어서 다가오더니 심화무라 앞에 유리창을 열어젖혔다.",
            },
            {"start": 13.61, "end": 15.213, "text": "눈에 냉기가 흘러들었다."},
        ],
        "language": "ko",
    }

    assert actual == expected
