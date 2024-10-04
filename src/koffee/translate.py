"""The koffee API."""

from datetime import datetime
import logging
from pathlib import Path
from typing import Optional, Union

from koffee.asr import transcribe_text
from koffee.exceptions import InvalidVideoFileError
from koffee.overlay import overlay_subtitles
from koffee.translator import translate_transcript
from koffee.utils.text_to_srt_converter import convert_text_to_srt


log = logging.getLogger(__name__)


def translate(
    video_file_path: Union[Path, str],
    batch_size: int = 16,
    compute_type: str = "float32",
    device: str = "cpu",
    model: str = "large-v3",
    output_dir: Optional[Path] = None,
    output_name: Optional[str] = None,
    srt: Optional[bool] = False,
    target_language: str = "en",
) -> Path:
    """Processes a video file for translation and subtitle overlay."""
    log.info("Processing video...")
    try:
        output_path = get_output_path(video_file_path, output_dir, output_name)

        transcript = transcribe_text(
            video_file_path, batch_size, compute_type, device, model
        )
        translated_transcript = translate_transcript(transcript, target_language)
        translated_srt_file = convert_text_to_srt(translated_transcript)

        overlay_subtitles(video_file_path, translated_srt_file, output_path)

        if srt is False:
            translated_srt_file.unlink()

        log.info("Finished processing video!")

        return output_path

    except RuntimeError as error:
        error_message = "Inputted file is not a valid video file or does not exist."
        raise InvalidVideoFileError(error_message) from error


def get_output_path(
    video_file_path: Union[Path, str],
    output_dir: Optional[Path],
    output_name: Optional[str],
) -> Path:
    """Gets the output path for the translated video file."""
    log.debug("output_name: " + repr(output_name))

    file_path = Path(video_file_path)
    file_dir = output_dir if output_dir is not None else file_path.parent
    file_name = (
        output_name
        if output_name is not None
        else f'{file_path.stem}_{datetime.today().strftime("%m-%d-%Y")}'
    )
    file_ext = file_path.suffix

    output_path = file_dir / (file_name + file_ext)
    log.debug("output_dir: " + repr(output_path))
    return output_path
