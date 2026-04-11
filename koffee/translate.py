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
from koffee.utils import extract_subtitle_track, parse_subtitle_file

log = logging.getLogger(__name__)

AUDIO_EXTENSIONS = {".mp3", ".wav", ".aac", ".flac", ".ogg", ".m4a"}
SUBTITLE_EXTENSIONS = {".srt", ".vtt", ".ass", ".ssa"}
VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv", ".wmv"}
SUPPORTED_EXTENSIONS = AUDIO_EXTENSIONS | VIDEO_EXTENSIONS


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
    _validate_api_key(config)

    if Path(video_file_path).suffix.lower() in SUBTITLE_EXTENSIONS:
        return _translate_subtitle_file(video_file_path, config, on_translate_progress)

    if config.use_embedded_subtitles:
        return _translate_embedded_subtitles(
            video_file_path, config, on_translate_progress
        )

    transcript = _transcribe(video_file_path, config, on_asr_progress)
    subtitle_file_path = _translate(transcript, config, on_translate_progress)
    output_path = _route_output(video_file_path, subtitle_file_path, config)

    return output_path


def _validate_file(video_file_path: Path | str) -> None:
    """Raises InvalidVideoFileError if the file does not exist or is not a file."""
    if not Path(video_file_path).exists() or not Path(video_file_path).is_file():
        error_message = "Input file is not valid or does not exist."
        log.error(error_message)
        raise InvalidVideoFileError(error_message)


def _validate_api_key(config: KoffeeConfig) -> None:
    """Raises ValueError if an LLM backend is selected without an API key."""
    if config.translator not in ("whisper", "ollama") and not config.api_key:
        error_message = (
            f"An API key is required when using the {config.translator} "
            "translation backend. Provide one with --api_key or set the appropriate "
            "environment variable."
        )
        raise ValueError(error_message)


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
        config.whisper_model,
        config.translator,
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


def _check_output_collision(output_path: Path, overwrite: bool) -> None:
    """Raises FileExistsError if the output file exists and overwrite is disabled."""
    if output_path.exists() and not overwrite:
        error_message = (
            f"Output file already exists: {output_path}. Use --overwrite to replace it."
        )
        raise FileExistsError(error_message)


def _route_output(
    video_file_path: Path | str,
    subtitle_file_path: Path,
    config: KoffeeConfig,
) -> Path:
    """Routes to subtitle output or video overlay based on file type and config."""
    is_audio = Path(video_file_path).suffix.lower() in AUDIO_EXTENSIONS
    has_overlay = not is_audio and config.overlay != "none"

    output_path = _get_output_path(
        video_file_path, config.output_dir, config.output_name, date_suffix=has_overlay
    )

    if has_overlay:
        _check_output_collision(output_path, config.overwrite)
        output_file_path = _finalize_video_output(
            subtitle_file_path,
            video_file_path,
            output_path,
            config.overlay,
            config.target_language,
        )
    else:
        target = output_path.with_suffix(f".{config.subtitle_format}")
        _check_output_collision(target, config.overwrite)
        output_file_path = _handle_subtitle_output(
            subtitle_file_path, output_path, config.subtitle_format
        )

    return output_file_path


def _translate_embedded_subtitles(
    video_file_path: Path | str,
    config: KoffeeConfig,
    on_progress: Callable[[float], None] | None,
) -> Path:
    """Extracts embedded subtitles from a video and translates them."""
    log.info("Extracting embedded subtitles from video.")

    extracted_path = extract_subtitle_track(
        video_file_path, config.subtitle_track_index
    )
    try:
        result = _translate_subtitle_file(extracted_path, config, on_progress)
    finally:
        extracted_path.unlink(missing_ok=True)

    return result


def _translate_subtitle_file(
    file_path: Path | str,
    config: KoffeeConfig,
    on_progress: Callable[[float], None] | None,
) -> Path:
    """Translates an existing subtitle file without ASR."""
    log.info("Detected subtitle file input, skipping transcription.")

    segments = parse_subtitle_file(file_path)
    translated_segments = translate_transcript(
        {"segments": segments, "language": config.source_language},
        config.target_language,
        config.api_key,
        on_progress,
        llm_model=config.llm_model,
        prompt=config.prompt,
        translator=config.translator,
    )
    translated = generate_subtitles(config.subtitle_format, translated_segments)
    output_path = _get_output_path(file_path, config.output_dir, config.output_name)
    output_subtitle_path = output_path.with_suffix(f".{config.subtitle_format}")
    _check_output_collision(output_subtitle_path, config.overwrite)
    translated.replace(output_subtitle_path)

    return output_subtitle_path


def _get_output_path(
    video_file_path: Path | str,
    output_dir: Path | None,
    output_name: str | None,
    date_suffix: bool = False,
) -> Path:
    """Gets the output path for the translated output file."""
    log.debug(f"output_name: {output_name!r}")

    file_path = Path(video_file_path)
    file_dir = output_dir if output_dir is not None else file_path.parent
    file_dir.mkdir(parents=True, exist_ok=True)

    if output_name is not None:
        file_name = output_name
    elif date_suffix:
        file_name = f"{file_path.stem}_{datetime.now().strftime('%m-%d-%Y')}"
    else:
        file_name = file_path.stem

    output_path = file_dir / (file_name + file_path.suffix)
    log.debug(f"output_dir: {output_path!r}")

    return output_path


def _get_segments(
    transcript: dict,
    config: KoffeeConfig,
    on_progress: Callable[[float], None] | None = None,
) -> list:
    """Returns translated or raw segments based on the translation backend."""
    if config.translator == "whisper":
        segments = transcript["segments"]
    else:
        segments = translate_transcript(
            transcript,
            config.target_language,
            config.api_key,
            on_progress,
            llm_model=config.llm_model,
            prompt=config.prompt,
            translator=config.translator,
            chunk_size=config.chunk_size,
            context_entries=config.context_entries,
        )

    return segments


def _finalize_video_output(
    subtitle_file_path: Path,
    video_file_path: Path,
    output_path: Path,
    overlay_mode: str = "soft",
    language: str = "en",
) -> Path:
    """Embeds subtitles into the video and deletes the subtitle file after."""
    output_video = overlay_subtitles(
        subtitle_file_path,
        video_file_path,
        output_path,
        mode=overlay_mode,
        language=language,
    )
    subtitle_file_path.unlink()
    log.info("Finished processing video!")

    return output_video


def _handle_subtitle_output(
    subtitle_file_path: Path, output_path: Path, subtitle_format: str
) -> Path:
    """Moves the subtitle file to the output path."""
    output_subtitle_path = output_path.with_suffix(f".{subtitle_format}")
    subtitle_file_path.replace(output_subtitle_path)
    log.info("Finished processing file!")

    return output_subtitle_path
