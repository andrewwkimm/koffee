"""Tests for ASR."""

from dataclasses import dataclass

from pytest_mock import MockerFixture

from koffee.asr import transcribe


@dataclass
class MockSegment:
    """Mock segment for testing."""

    start: float
    end: float
    text: str


def test_transcribe(mocker: MockerFixture) -> None:
    """Tests a given video file is transcribed properly."""
    mock_segment = MockSegment(start=0.0, end=7.0, text="Mock transcription text.")
    mock_segment.text = "Mock transcription text."

    mock_model = mocker.MagicMock()
    mock_model.transcribe.return_value = (
        [mock_segment],
        mocker.MagicMock(language="ko"),
    )

    mocker.patch("koffee.asr.WhisperModel", return_value=mock_model)

    result = transcribe("mock_video_file.mp4", "int8", "auto", "large-v3", "whisper")

    mock_model.transcribe.assert_called_once_with(
        "mock_video_file.mp4",
        task="translate",
        word_timestamps=True,
        vad_filter=True,
    )

    assert result["language"] == "ko"
    assert result["segments"][0]["text"] == "Mock transcription text."


def test_transcribe_reports_progress(mocker: MockerFixture) -> None:
    """Tests that progress callback is called during transcription."""
    mock_segment = MockSegment(start=0.0, end=5.0, text="Hello.")

    mock_model = mocker.MagicMock()
    mock_model.transcribe.return_value = (
        [mock_segment],
        mocker.MagicMock(language="ko"),
    )

    mocker.patch("koffee.asr.WhisperModel", return_value=mock_model)
    mocker.patch("koffee.asr.get_video_duration", return_value=10.0)

    progress_calls = []
    transcribe(
        "mock_video_file.mp4",
        "int8",
        "auto",
        "large-v3",
        "whisper",
        on_progress=progress_calls.append,
    )

    assert progress_calls == [0.5, 1.0]
