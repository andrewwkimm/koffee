"""Tests for text translation."""

from koffee.translator import translate_transcript


def test_translate_transcript() -> None:
    """Tests that the transcript was translated properly."""
    sample_transcript = {
        "segments": [
            {"text": "시대를 초월한 마음."},
            {"text": "음식."},
        ],
        "language": "ko",
    }

    actual = translate_transcript(sample_transcript, target_language="en")
    expected = [
        {"text": "A mind beyond its time."},
        {"text": "Food."},
    ]

    assert actual == expected
