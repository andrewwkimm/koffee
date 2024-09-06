"""The koffee API."""

from pathlib import Path
from typing import Optional, Union

from koffee.asr import transcribe_text
from koffee.overlay import overlay_subtitles
from koffee.translator import translate_transcript
from koffee.utils import convert_json_to_srt


def translate(
    video_file_path: Union[Path, str],
    batch_size: int = 16,
    device: str = "cpu",
    compute_type: str = "float32",
    output_path: Optional[Union[Path, str]] = None,
    whisper_arch: str = "large-v3",
) -> Union[Path, str]:
    """Processes a video file for translation and subtitle overlay."""
    video_file_path = Path(video_file_path)

    if output_path is None:
        file_name = f"{video_file_path.stem}_translated{video_file_path.suffix}"
        output_path = video_file_path.parent / file_name

    transcript = transcribe_text(
        video_file_path, batch_size, device, compute_type, whisper_arch
    )
    translated_transcript = translate_transcript(transcript)
    translated_srt_file = convert_json_to_srt(translated_transcript)

    overlay_subtitles(video_file_path, translated_srt_file, output_path)

    return output_path
