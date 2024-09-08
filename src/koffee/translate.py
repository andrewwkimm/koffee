"""The koffee API."""

from datetime import datetime
import os
from pathlib import Path
from typing import Optional, Union

from koffee.asr import transcribe_text
from koffee.overlay import overlay_subtitles
from koffee.translator import translate_transcript
from koffee.utils.text_to_srt_converter import convert_text_to_srt


def translate(
    video_file_path: Union[Path, str],
    batch_size: int = 16,
    compute_type: str = "float32",
    device: str = "cpu",
    model: str = "large-v3",
    output_dir: Optional[Path] = None,
    output_name: Optional[str] = None,
) -> Union[Path, str]:
    """Processes a video file for translation and subtitle overlay."""
    output_path = get_output_path(video_file_path, output_dir, output_name)

    transcript = transcribe_text(
        video_file_path, batch_size, compute_type, device, model
    )
    translated_transcript = translate_transcript(transcript)
    translated_srt_file = convert_text_to_srt(translated_transcript)

    overlay_subtitles(video_file_path, translated_srt_file, output_path)

    os.remove(translated_srt_file)

    return output_path


def get_output_path(
    video_file_path: Union[Path, str],
    output_dir: Optional[Path],
    output_name: Optional[str],
) -> Path:
    """Gets the output path for the translated video file."""
    file_path = Path(video_file_path)

    if output_dir is None:
        file_dir = file_path.parent

    if output_name is None:
        file_name = f'{file_path.stem}_{datetime.today().strftime("%m-%d-%Y")}'

    file_ext = file_path.suffix

    output_path = file_dir / (file_name + file_ext)
    return output_path
