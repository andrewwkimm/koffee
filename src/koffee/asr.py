"""Text extractor from audio."""

import contextlib
import logging
from pathlib import Path
from typing import Union

logging.getLogger("speechbrain").setLevel(logging.ERROR)

import whisperx  # noqa: E402


log = logging.getLogger(__name__)


def transcribe_text(
    video_file: Union[Path, str],
    batch_size: int,
    compute_type: str,
    device: str,
    model: str,
) -> dict:
    """Transcribes text from a video file."""
    logging.getLogger("pytorch_lightning").setLevel(logging.ERROR)

    log.info("Transcribing text.")

    # Redirect stdout to suppress overly verbose messages from whisperx
    with open("/dev/null", "w") as null_fd:
        with contextlib.redirect_stdout(null_fd):
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
