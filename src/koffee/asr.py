"""Text extractor from audio."""

import logging
from dataclasses import asdict

from faster_whisper import WhisperModel  # noqa: E402

log = logging.getLogger(__name__)


def transcribe_text(
    video_file: str,
    compute_type: str,
    device: str,
    model: str,
) -> dict:
    """Transcribes text from a video file."""
    log.info("Transcribing text.")

    loaded_model = WhisperModel(
        model_size_or_path=model,
        device=device,
        compute_type=compute_type,
        local_files_only=False,
    )
    segments, info = loaded_model.transcribe(video_file)

    transcript = {"segments": [asdict(segment) for segment in segments]}
    transcript["language"] = info.language
    return transcript
