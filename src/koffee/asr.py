"""Text extractor from audio."""

import json
from pathlib import Path
from typing import Union

import whisperx


def transcribe_text(
    video_file: Union[Path, str],
    batch_size=16,
    device="cpu",
    compute_type="float32",
    whisper_arch="large-v3",
) -> json:
    """Transcribes text from a video file."""
    model = whisperx.load_model(
        whisper_arch=whisper_arch, device=device, compute_type=compute_type
    )
    audio = whisperx.load_audio(video_file)
    result = model.transcribe(audio, batch_size=batch_size)

    model_a, metadata = whisperx.load_align_model(
        language_code=result["language"], device=device
    )
    aligned_result = whisperx.align(
        result["segments"],
        model_a,
        metadata,
        audio,
        device,
        return_char_alignments=False,
    )
    return aligned_result
