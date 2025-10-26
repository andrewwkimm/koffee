"""The koffee API."""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from koffee.asr import transcribe_text
from koffee.data.config import KoffeeConfig
from koffee.exceptions import InvalidVideoFileError
from koffee.overlay import overlay_subtitles
from koffee.subtitle import generate_subtitles
from koffee.translator import translate_transcript

log = logging.getLogger(__name__)


def translate(
    video_file_path: Path | str,
    config: KoffeeConfig | None = None,
    **kwargs: Any,
) -> Path | str:
    """Processes a video file for translation and subtitle overlay."""
    log.info("Processing video...")

    if not Path(video_file_path).exists() or not Path(video_file_path).is_file():
        error_message = "Inputted file is not a valid video file or does not exist."
        log.error(error_message)
        raise InvalidVideoFileError(error_message)

    if config is None:
        config = KoffeeConfig(**kwargs)
    else:
        config = KoffeeConfig(**{**config.model_dump(), **kwargs})

    output_path = get_output_path(
        video_file_path, config.output_dir, config.output_name
    )

    transcript = transcribe_text(
        str(video_file_path),
        config.compute_type,
        config.device,
        config.model,
    )
    translated_transcript = translate_transcript(transcript, config.target_language)
    subtitle_file_path = generate_subtitles(
        config.subtitle_format, translated_transcript
    )

    output_video_file_path = overlay_subtitles(
        subtitle_file_path, video_file_path, output_path
    )

    if config.subtitles is False:
        subtitle_file_path.unlink()

    log.info("Finished processing video!")

    return output_video_file_path


def get_output_path(
    video_file_path: Path | str,
    output_dir: Path | None,
    output_name: str | None,
) -> Path:
    """Gets the output path for the translated video file."""
    log.debug(f"output_name: {output_name!r}")

    file_path = Path(video_file_path)
    file_dir = output_dir if output_dir is not None else file_path.parent
    file_name = (
        output_name
        if output_name is not None
        else f"{file_path.stem}_{datetime.today().strftime('%m-%d-%Y')}"
    )
    file_ext = file_path.suffix

    output_path = file_dir / (file_name + file_ext)
    log.debug(f"output_dir: {output_path!r}")
    return output_path
