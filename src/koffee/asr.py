"""Text extractor from audio."""

from pathlib import Path
from typing import Union

import whisperx


def transcribe_text(
    video_file: Union[Path, str],
    batch_size: int,
    compute_type: str,
    device: str,
    model: str,
) -> dict:
    """Transcribes text from a video file."""
    loaded_model = whisperx.load_model(
        whisper_arch=model, device=device, compute_type=compute_type
    )
    audio = whisperx.load_audio(video_file)
    transcript = loaded_model.transcribe(audio, batch_size=batch_size)

    model_a, metadata = whisperx.load_align_model(
        language_code=transcript["language"], device=device
    )
    aligned_transcript = whisperx.align(
        transcript["segments"],
        model_a,
        metadata,
        audio,
        device,
        return_char_alignments=False,
    )
    aligned_transcript["language"] = transcript["language"]
    return aligned_transcript
