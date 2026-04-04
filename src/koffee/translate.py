"""The koffee API."""

import logging
from collections.abc import Callable
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

AUDIO_EXTENSIONS = {".mp3", ".wav", ".aac", ".flac", ".ogg", ".m4a"}


def translate(
    video_file_path: Path | str,
    config: KoffeeConfig | None = None,
    on_asr_progress: Callable[[float], None] | None = None,
    on_translate_progress: Callable[[float], None] | None = None,
    **kwargs: Any,
) -> Path | str:
    """Processes a video or audio file for translation and subtitle generation."""
    log.info("Translating file...")

    _validate_file(video_file_path)
    config = _apply_config_overrides(config, kwargs)
    transcript = _transcribe(video_file_path, config, on_asr_progress)
    subtitle_file_path = _translate(transcript, config, on_translate_progress)
    output_path = _route_output(video_file_path, subtitle_file_path, config)

    return output_path


def _validate_file(video_file_path: Path | str) -> None:
    """Raises InvalidVideoFileError if the file does not exist or is not a file."""
    if not Path(video_file_path).exists() or not Path(video_file_path).is_file():
        error_message = "Inputted file is not a valid video file or does not exist."
        log.error(error_message)
        raise InvalidVideoFileError(error_message)


def _apply_config_overrides(config: KoffeeConfig | None, kwargs: dict) -> KoffeeConfig:
    """Resolves config, applying any kwarg overrides on top of an existing config."""
    if config is None:
        config = KoffeeConfig(**kwargs)
    else:
        config = KoffeeConfig(**{**config.model_dump(), **kwargs})

    return config


def _transcribe(
    video_file_path: Path | str,
    config: KoffeeConfig,
    on_progress: Callable[[float], None] | None,
) -> dict:
    """Transcribes audio from the file, returning the raw transcript."""
    transcript = transcribe_text(
        str(video_file_path),
        config.compute_type,
        config.device,
        config.model,
        config.translation_backend,
        on_progress=on_progress,
    )

    return transcript


def _translate(
    transcript: dict,
    config: KoffeeConfig,
    on_progress: Callable[[float], None] | None,
) -> Path:
    """Translates transcript segments and writes the subtitle file."""
    segments = _get_segments(transcript, config, on_progress=on_progress)
    subtitle_file_path = generate_subtitles(config.subtitle_format, segments)

    return subtitle_file_path


def _route_output(
    video_file_path: Path | str,
    subtitle_file_path: Path,
    config: KoffeeConfig,
) -> Path:
    """Routes to subtitle output or video overlay based on file type and config."""
    output_path = _get_output_path(
        video_file_path, config.output_dir, config.output_name
    )
    is_audio = Path(video_file_path).suffix.lower() in AUDIO_EXTENSIONS

    if is_audio or not config.overlay_video:
        output_file_path = _handle_subtitle_output(
            subtitle_file_path, output_path, config.subtitle_format
        )
    else:
        output_file_path = _finalize_video_output(
            subtitle_file_path, video_file_path, output_path
        )

    return output_file_path


def _get_output_path(
    video_file_path: Path | str,
    output_dir: Path | None,
    output_name: str | None,
) -> Path:
    """Gets the output path for the translated output file."""
    log.debug(f"output_name: {output_name!r}")

    file_path = Path(video_file_path)
    file_dir = output_dir if output_dir is not None else file_path.parent
    is_audio = file_path.suffix.lower() in AUDIO_EXTENSIONS

    if output_name is not None:
        file_name = output_name
    elif is_audio:
        file_name = file_path.stem
    else:
        file_name = f"{file_path.stem}_{datetime.today().strftime('%m-%d-%Y')}"

    output_path = file_dir / (file_name + file_path.suffix)
    log.debug(f"output_dir: {output_path!r}")

    return output_path


def _get_segments(
    transcript: dict,
    config: KoffeeConfig,
    on_progress: Callable[[float], None] | None = None,
) -> list:
    """Returns translated or raw segments based on the translation backend."""
    if config.translation_backend == "whisper":
        segments = transcript["segments"]
    else:
        segments = translate_transcript(
            transcript, config.target_language, config.api_key, on_progress
        )

    return segments


def _finalize_video_output(
    subtitle_file_path: Path,
    video_file_path: Path,
    output_path: Path,
) -> Path:
    """Embeds subtitles into the video as a soft subtitle track and deletes it after."""
    output_video = overlay_subtitles(subtitle_file_path, video_file_path, output_path)
    subtitle_file_path.unlink()
    log.info("Finished processing video!")

    return output_video


def _handle_subtitle_output(
    subtitle_file_path: Path, output_path: Path, subtitle_format: str
) -> Path:
    """Moves the subtitle file to the output path."""
    output_subtitle_path = output_path.with_suffix(f".{subtitle_format}")
    subtitle_file_path.rename(output_subtitle_path)
    log.info("Finished processing file!")

    return output_subtitle_path
