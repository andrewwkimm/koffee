"""Tests for ASR."""

from dataclasses import dataclass

from pytest_mock import MockerFixture

from koffee.asr import transcribe_text


@dataclass
class MockSegment:
    """Mock segment for testing."""

    start: float
    end: float
    text: str


def test_transcribe_text(mocker: MockerFixture) -> None:
    """Tests text is transcribed properly for a given video file."""
    mock_segment = MockSegment(start=0.0, end=7.0, text="Mock transcription text.")
    mock_segment.text = "Mock transcription text."

    mock_model = mocker.MagicMock()
    mock_model.transcribe.return_value = (
        [mock_segment],
        mocker.MagicMock(language="ko"),
    )

    mocker.patch("koffee.asr.WhisperModel", return_value=mock_model)

    result = transcribe_text(
        "mock_video_file.mp4", "int8", "auto", "large-v3", "whisper"
    )

    mock_model.transcribe.assert_called_once_with(
        "mock_video_file.mp4",
        task="translate",
        word_timestamps=True,
        vad_filter=True,
    )

    assert result["language"] == "ko"
    assert result["segments"][0]["text"] == "Mock transcription text."
