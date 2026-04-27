"""The koffee API."""

import logging
import shutil
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from koffee.asr import transcribe
from koffee.embed import embed_subtitles
from koffee.exceptions import (
    IncompatibleOptionsError,
    InvalidVideoFileError,
    MissingApiKeyError,
    MissingDependencyError,
    TranslationError,
    UnsupportedFileError,
)
from koffee.schemas.config import KoffeeConfig
from koffee.schemas.types import Segment, Transcript
from koffee.subtitle import (
    extract_subtitle_track,
    generate_subtitles,
    get_subtitle_tracks,
    parse_subtitle_file,
)
from koffee.translator import translate

log = logging.getLogger(__name__)

AUDIO_EXTENSIONS = {".mp3", ".wav", ".aac", ".flac", ".ogg", ".m4a"}
SUBTITLE_EXTENSIONS = {".srt", ".vtt", ".ass", ".ssa"}
VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv", ".wmv"}
SUPPORTED_EXTENSIONS = AUDIO_EXTENSIONS | VIDEO_EXTENSIONS


def run(
    input_path: Path | str,
    config: KoffeeConfig | None = None,
    on_asr_progress: Callable[[float], None] | None = None,
    on_translate_progress: Callable[[float], None] | None = None,
    **kwargs: Any,
) -> Path | str:
    """Processes a video or audio file for translation and subtitle generation."""
    log.info("Translating file...")

    config = _apply_config_overrides(config, kwargs)
    _validate_inputs(input_path, config)

    if Path(input_path).suffix.lower() in SUBTITLE_EXTENSIONS:
        return _translate_subtitle_file(input_path, config, on_translate_progress)

    if config.use_embedded_subtitles:
        return _translate_embedded_subtitles(input_path, config, on_translate_progress)

    transcript = _transcribe(input_path, config, on_asr_progress)
    try:
        subtitle_path = _translate(transcript, config, on_translate_progress)
    except Exception as exc:
        raise TranslationError(str(exc), transcript["segments"]) from exc
    output_path = _route_output(input_path, subtitle_path, config)

    return output_path


def _apply_config_overrides(config: KoffeeConfig | None, kwargs: dict) -> KoffeeConfig:
    """Resolves config, applying any kwarg overrides on top of an existing config."""
    if config is None:
        config = KoffeeConfig(**kwargs)
    else:
        config = KoffeeConfig(**{**config.model_dump(), **kwargs})

    return config


def _route_output(
    input_path: Path | str,
    subtitle_path: Path,
    config: KoffeeConfig,
) -> Path:
    """Routes to subtitle output or video embed based on file type and config."""
    is_audio = Path(input_path).suffix.lower() in AUDIO_EXTENSIONS
    has_embed = not is_audio and config.embed != "none"

    output_path = _get_output_path(
        input_path, config.output_dir, config.output_name, date_suffix=has_embed
    )

    if has_embed:
        _check_output_collision(output_path, config.overwrite)
        result_path = _finalize_video_output(
            subtitle_path,
            input_path,
            output_path,
            config.embed,
            config.target_language,
        )
    else:
        result_path = _write_output(
            subtitle_path,
            input_path,
            config.subtitle_format,
            config.output_dir,
            config.output_name,
            config.overwrite,
        )

    return result_path


def _finalize_video_output(
    subtitle_path: Path,
    input_path: Path,
    output_path: Path,
    embed_mode: str = "soft",
    language: str = "en",
) -> Path:
    """Embeds subtitles into the video and deletes the subtitle file after."""
    output_video = embed_subtitles(
        subtitle_path,
        input_path,
        output_path,
        mode=embed_mode,
        language=language,
    )
    subtitle_path.unlink()
    log.info("Finished processing video!")

    return output_video


def _write_output(
    source_path: Path,
    input_path: Path | str,
    subtitle_format: str,
    output_dir: Path | None,
    output_name: str | None,
    overwrite: bool,
) -> Path:
    """Moves a generated subtitle file to its resolved output location."""
    base_path = _get_output_path(input_path, output_dir, output_name)
    target_path = base_path.with_suffix(f".{subtitle_format}")

    try:
        _check_output_collision(target_path, overwrite)
    except FileExistsError:
        source_path.unlink(missing_ok=True)
        raise

    source_path.replace(target_path)
    log.info("Finished processing file!")

    return target_path


def _check_output_collision(output_path: Path, overwrite: bool) -> None:
    """Raises FileExistsError if the output file exists and overwrite is disabled."""
    if output_path.exists() and not overwrite:
        error_message = (
            f"Output file already exists: {output_path}. Use --overwrite to replace it."
        )
        raise FileExistsError(error_message)


def _get_output_path(
    input_path: Path | str,
    output_dir: Path | None,
    output_name: str | None,
    date_suffix: bool = False,
) -> Path:
    """Gets the output path for the translated output file."""
    log.debug(f"output_name: {output_name!r}")

    file_path = Path(input_path)
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


def _transcribe(
    input_path: Path | str,
    config: KoffeeConfig,
    on_progress: Callable[[float], None] | None,
) -> Transcript:
    """Transcribes audio from the file, returning the raw transcript."""
    task = "translate" if config.provider == "whisper" else "transcribe"
    transcript = transcribe(
        str(input_path),
        config.compute_type,
        config.device,
        config.whisper_model,
        task,
        on_progress=on_progress,
        vad_filter=config.vad_filter,
    )

    return transcript


def _translate(
    transcript: Transcript,
    config: KoffeeConfig,
    on_progress: Callable[[float], None] | None,
) -> Path:
    """Translates transcript segments and writes the subtitle file."""
    segments = _get_segments(transcript, config, on_progress=on_progress)
    subtitle_path = generate_subtitles(config.subtitle_format, segments)

    return subtitle_path


def _get_segments(
    transcript: Transcript,
    config: KoffeeConfig,
    on_progress: Callable[[float], None] | None = None,
) -> list[Segment]:
    """Returns translated or raw segments based on the translation backend."""
    if config.provider == "whisper":
        segments = transcript["segments"]
    else:
        segments = translate(
            transcript,
            config.target_language,
            config.api_key,
            on_progress,
            llm_model=config.llm_model,
            prompt=config.prompt,
            provider=config.provider,
            chunk_size=config.chunk_size,
            context_size=config.context_size,
            sleep_requests=config.sleep_requests,
        )

    return segments


def _translate_embedded_subtitles(
    input_path: Path | str,
    config: KoffeeConfig,
    on_progress: Callable[[float], None] | None,
) -> Path:
    """Extracts embedded subtitles from a video and translates them."""
    log.info("Extracting embedded subtitles from video.")

    extracted_path = extract_subtitle_track(input_path, config.subtitle_track_index)
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
    translated_segments = translate(
        {"segments": segments, "language": config.source_language},
        config.target_language,
        config.api_key,
        on_progress,
        llm_model=config.llm_model,
        prompt=config.prompt,
        provider=config.provider,
        sleep_requests=config.sleep_requests,
    )
    translated_path = generate_subtitles(config.subtitle_format, translated_segments)
    output_subtitle_path = _write_output(
        translated_path,
        file_path,
        config.subtitle_format,
        config.output_dir,
        config.output_name,
        config.overwrite,
    )

    return output_subtitle_path


def _validate_inputs(input_path: Path | str, config: KoffeeConfig) -> None:
    """Runs pre-flight checks on the input file, dependencies, and config options."""
    _validate_file(input_path)

    suffix = Path(input_path).suffix.lower()
    allowed = SUPPORTED_EXTENSIONS | SUBTITLE_EXTENSIONS
    if suffix not in allowed:
        error_message = (
            f"Unsupported file type: {suffix!r}. "
            f"Supported extensions: {', '.join(sorted(allowed))}"
        )
        raise UnsupportedFileError(error_message)

    is_video = suffix in VIDEO_EXTENSIONS

    if config.embed != "none" and not is_video:
        error_message = "--embed is only supported for video file inputs."
        raise IncompatibleOptionsError(error_message)

    if config.use_embedded_subtitles and not is_video:
        error_message = (
            "--use-embedded-subtitles is only supported for video file inputs."
        )
        raise IncompatibleOptionsError(error_message)

    needs_ffmpeg = config.embed != "none" or config.use_embedded_subtitles
    if needs_ffmpeg and shutil.which("ffmpeg") is None:
        error_message = (
            "ffmpeg was not found on PATH. Install ffmpeg to use --embed or "
            "--use-embedded-subtitles."
        )
        raise MissingDependencyError(error_message)

    if config.use_embedded_subtitles:
        if shutil.which("ffprobe") is None:
            error_message = (
                "ffprobe was not found on PATH. Install ffmpeg to use "
                "--use-embedded-subtitles."
            )
            raise MissingDependencyError(error_message)
        if not get_subtitle_tracks(input_path):
            error_message = f"No embedded subtitle tracks found in {input_path}."
            raise IncompatibleOptionsError(error_message)

    _validate_api_key(config)
    _validate_output_path(input_path, config)


def _validate_api_key(config: KoffeeConfig) -> None:
    """Raises MissingApiKeyError if an LLM backend is selected without an API key."""
    if config.provider not in ("whisper", "ollama") and not config.api_key:
        error_message = (
            f"An API key is required when using the {config.provider} "
            "translation backend. Provide one with --api_key or set the appropriate "
            "environment variable."
        )
        raise MissingApiKeyError(error_message)


def _validate_file(input_path: Path | str) -> None:
    """Raises InvalidVideoFileError if the file does not exist or is not a file."""
    if not Path(input_path).exists() or not Path(input_path).is_file():
        error_message = "Input file is not valid or does not exist."
        log.error(error_message)
        raise InvalidVideoFileError(error_message)


def _validate_output_path(input_path: Path | str, config: KoffeeConfig) -> None:
    """Ensures the resolved output path is writable and not already occupied."""
    input_suffix = Path(input_path).suffix.lower()
    is_video = input_suffix in VIDEO_EXTENSIONS
    has_embed = (
        is_video and not config.use_embedded_subtitles and config.embed != "none"
    )

    base_path = _get_output_path(
        input_path, config.output_dir, config.output_name, date_suffix=has_embed
    )
    output_path = (
        base_path if has_embed else base_path.with_suffix(f".{config.subtitle_format}")
    )

    _check_output_collision(output_path, config.overwrite)
