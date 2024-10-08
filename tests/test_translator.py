"""Tests for text translation."""

from koffee.translator import translate_transcript


def test_translate_transcript() -> None:
    """Tests that the transcript was translated properly."""
    sample_transcript = {
        "segments": [
            {"text": "안녕하세요."},
            {"text": "음식."},
        ],
        "language": "ko",
    }

    actual = translate_transcript(sample_transcript, target_language="en")
    expected = [
        {"text": "Hello."},
        {"text": "Food."},
    ]

    assert actual == expected
