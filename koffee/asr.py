"""Text extractor from audio."""

import logging
from collections.abc import Callable
from dataclasses import asdict

from faster_whisper import WhisperModel

from koffee.schemas.types import Segment, Transcript
from koffee.utils import get_video_duration

log = logging.getLogger(__name__)


def transcribe(
    video_file: str,
    compute_type: str,
    device: str,
    model: str,
    provider: str,
    on_progress: Callable[[float], None] | None = None,
    vad_filter: bool = True,
) -> Transcript:
    """Transcribes a video or audio file."""
    log.info("Transcribing file.")

    loaded_model = _load_model(compute_type, device, model)
    segments, info = _run_transcription(loaded_model, video_file, provider, vad_filter)

    transcript = {
        "segments": _consume_segments(segments, video_file, on_progress),
        "language": info.language,
    }

    return transcript


def _load_model(compute_type: str, device: str, model: str) -> WhisperModel:
    """Loads and returns a Whisper model with the given configuration."""
    loaded_model = WhisperModel(
        model_size_or_path=model,
        device=device,
        compute_type=compute_type,
        local_files_only=False,
    )

    return loaded_model


def _run_transcription(
    loaded_model: WhisperModel, video_file: str, provider: str, vad_filter: bool
) -> tuple:
    """Runs transcription on the video file, returning segments and info."""
    task = "translate" if provider == "whisper" else "transcribe"
    segments, info = loaded_model.transcribe(
        video_file, task=task, word_timestamps=True, vad_filter=vad_filter
    )

    return segments, info


def _consume_segments(
    segments, video_file: str, on_progress: Callable[[float], None] | None
) -> list[Segment]:
    """Consumes the segment generator, reporting progress as each segment is yielded."""
    duration = get_video_duration(video_file) if on_progress else None
    result = []
    for segment in segments:
        result.append(asdict(segment))
        if on_progress and duration:
            on_progress(min(segment.end / duration, 1.0))

    if on_progress:
        on_progress(1.0)

    return result
