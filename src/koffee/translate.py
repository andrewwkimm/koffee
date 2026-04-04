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

AUDIO_EXTENSIONS = {".mp3", ".wav", ".aac", ".flac", ".ogg", ".m4a"}


def translate(
    video_file_path: Path | str,
    config: KoffeeConfig | None = None,
    **kwargs: Any,
) -> Path | str:
    """Processes a video file for translation and subtitle overlay."""
    log.info("Translating file...")

    if not Path(video_file_path).exists() or not Path(video_file_path).is_file():
        error_message = "Inputted file is not a valid video file or does not exist."
        log.error(error_message)
        raise InvalidVideoFileError(error_message)

    config = _apply_config_overrides(config, kwargs)

    output_path = _get_output_path(
        video_file_path, config.output_dir, config.output_name
    )

    transcript = transcribe_text(
        str(video_file_path),
        config.compute_type,
        config.device,
        config.model,
        config.translation_backend,
    )

    segments = _get_segments(transcript, config)
    subtitle_file_path = generate_subtitles(config.subtitle_format, segments)

    is_audio = Path(video_file_path).suffix.lower() in AUDIO_EXTENSIONS
    if is_audio:
        return _handle_audio_output(
            subtitle_file_path, output_path, config.subtitle_format
        )

    return _finalize_video_output(
        subtitle_file_path, video_file_path, output_path, config.subtitles
    )


def _apply_config_overrides(config: KoffeeConfig | None, kwargs: dict) -> KoffeeConfig:
    """Resolves config, applying any kwarg overrides on top of an existing config."""
    if config is None:
        return KoffeeConfig(**kwargs)
    return KoffeeConfig(**{**config.model_dump(), **kwargs})


def _finalize_video_output(
    subtitle_file_path: Path,
    video_file_path: Path,
    output_path: Path,
    keep_subtitles: bool,
) -> Path:
    """Overlays subtitles onto the video and optionally removes the subtitle file."""
    output_video = overlay_subtitles(subtitle_file_path, video_file_path, output_path)
    if not keep_subtitles:
        subtitle_file_path.unlink()
    log.info("Finished processing video!")
    return output_video


def _get_output_path(
    video_file_path: Path | str,
    output_dir: Path | None,
    output_name: str | None,
) -> Path:
    """Gets the output path for the translated video file."""
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


def _get_segments(transcript: dict, config: KoffeeConfig) -> list:
    """Returns translated or raw segments based on the translation backend."""
    if config.translation_backend == "whisper":
        return transcript["segments"]
    return translate_transcript(transcript, config.target_language, config.api_key)


def _handle_audio_output(
    subtitle_file_path: Path, output_path: Path, subtitle_format: str
) -> Path:
    """Moves the subtitle file to the output path for audio file inputs."""
    output_subtitle_path = output_path.with_suffix(f".{subtitle_format}")
    subtitle_file_path.rename(output_subtitle_path)
    log.info("Finished processing audio file!")
    return output_subtitle_path
