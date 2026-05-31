"""Text extractor from audio."""

import logging
import subprocess
from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path

from faster_whisper import WhisperModel

from koffee.schemas.types import Transcript

log = logging.getLogger(__name__)


def transcribe(
    video_file: str,
    compute_type: str,
    device: str,
    model: str,
    task: str,
    on_progress: Callable[[float], None] | None = None,
    vad_filter: bool = True,
) -> Transcript:
    """Transcribes a video or audio file."""
    log.info("Transcribing file.")

    loaded_model = WhisperModel(
        model_size_or_path=model,
        device=device,
        compute_type=compute_type,
        local_files_only=False,
    )

    segments, info = loaded_model.transcribe(
        video_file, task=task, word_timestamps=True, vad_filter=vad_filter
    )

    duration = _get_video_duration(video_file) if on_progress else None
    result = []
    for segment in segments:
        result.append(asdict(segment))
        if on_progress and duration:
            on_progress(min(segment.end / duration, 1.0))
    if on_progress:
        on_progress(1.0)

    transcript = {
        "segments": result,
        "language": info.language,
    }
    return transcript


def _get_video_duration(video_path: Path | str) -> float:
    """Gets the duration in seconds using ffprobe."""
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(video_path),
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
    except FileNotFoundError:
        log.error("ffprobe not found. Please install ffmpeg to use this feature.")
        raise
    except subprocess.TimeoutExpired:
        log.error("ffprobe timed out while getting video duration.")
        raise

    stdout = result.stdout.strip()
    if not stdout:
        return 0.0

    video_duration = float(stdout)
    return video_duration
