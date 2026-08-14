"""The koffee API."""

import logging
import shutil
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory
from typing import Any

from anthropic import APIError as AnthropicAPIError
from google.genai.errors import APIError as GeminiAPIError
from openai import OpenAIError

from koffee.asr import transcribe
from koffee.embed import embed_subtitles
from koffee.exceptions import (
    IncompatibleOptionsError,
    InvalidVideoFileError,
    MissingApiKeyError,
    MissingDependencyError,
    SubtitleEmbedError,
    TranslationError,
    TranslationIntegrityError,
    UnsupportedFileError,
)
from koffee.schemas.config import KoffeeConfig
from koffee.schemas.domain import Transcript
from koffee.subtitle import (
    SUBTITLE_EXTENSIONS,
    extract_subtitle_track,
    generate_subtitles,
    get_subtitle_tracks,
    parse_subtitle_file,
)
from koffee.translator import translate

log = logging.getLogger(__name__)

AUDIO_EXTENSIONS = {".mp3", ".wav", ".aac", ".flac", ".ogg", ".m4a"}
VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv", ".wmv"}
SUPPORTED_EXTENSIONS = AUDIO_EXTENSIONS | VIDEO_EXTENSIONS


def run(
    input_path: Path | str,
    config: KoffeeConfig | None = None,
    on_asr_progress: Callable[[float], None] | None = None,
    on_translate_progress: Callable[[float], None] | None = None,
    **kwargs: Any,
) -> Path | str:
    """Processes one media or subtitle file into translated output."""
    log.info("Translating file...")

    if config is None:
        config = KoffeeConfig(**kwargs)
    else:
        config = KoffeeConfig(**{**config.model_dump(), **kwargs})

    _check_preconditions(input_path, config)

    if Path(input_path).suffix.lower() in SUBTITLE_EXTENSIONS:
        subtitle_path = _translate_subtitle_file(
            input_path,
            config,
            on_translate_progress,
        )
        return _route_output(input_path, subtitle_path, config)

    if config.use_embedded_subtitles:
        return _translate_embedded_subtitles(
            input_path,
            config,
            on_translate_progress,
        )

    task = "translate" if config.provider == "whisper" else "transcribe"
    transcript = transcribe(
        str(input_path),
        config.compute_type,
        config.device,
        config.whisper_model,
        task,
        on_progress=on_asr_progress,
        vad_filter=config.vad_filter,
        language=_resolve_asr_language(config.source_language),
    )
    subtitle_path = _translate_with_failure_context(
        transcript,
        config,
        on_translate_progress,
    )
    return _route_output(input_path, subtitle_path, config)


def _resolve_asr_language(
    source_language: str,
) -> str | None:
    """Returns no constraint for automatic detection."""
    return None if source_language == "auto" else source_language


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
        result_path = _write_embedded_video(
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


def _write_embedded_video(
    subtitle_path: Path,
    input_path: Path,
    output_path: Path,
    embed_mode: str = "soft",
    language: str = "en",
) -> Path:
    """Publishes an embedded video only after FFmpeg succeeds."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(
        prefix=f".{output_path.stem}.",
        suffix=output_path.suffix,
        dir=output_path.parent,
        delete=False,
    ) as temporary_file:
        temporary_path = Path(temporary_file.name)
    temporary_path.unlink()

    published = False
    try:
        embedded_path = Path(
            embed_subtitles(
                subtitle_path,
                input_path,
                temporary_path,
                mode=embed_mode,
                language=language,
            )
        )
        if not embedded_path.is_file():
            error_message = "FFmpeg did not produce the expected output video."
            raise SubtitleEmbedError(error_message)

        embedded_path.replace(output_path)
        published = True
    finally:
        if not published:
            temporary_path.unlink(missing_ok=True)

    subtitle_path.unlink()
    log.info("Finished processing video!")
    return output_path


def _write_output(
    source_path: Path,
    input_path: Path | str,
    subtitle_format: str,
    output_dir: Path | None,
    output_name: str | None,
    overwrite: bool,
) -> Path:
    """Copies a subtitle to an atomically published output."""
    base_path = _get_output_path(
        input_path,
        output_dir,
        output_name,
    )
    target_path = base_path.with_suffix(f".{subtitle_format}")

    try:
        _check_output_collision(target_path, overwrite)
    except FileExistsError:
        source_path.unlink(missing_ok=True)
        raise

    with NamedTemporaryFile(
        prefix=f".{target_path.name}.",
        dir=target_path.parent,
        delete=False,
    ) as temporary_file:
        temporary_path = Path(temporary_file.name)

    published = False
    try:
        shutil.copy2(source_path, temporary_path)
        temporary_path.replace(target_path)
        published = True
    finally:
        if not published:
            temporary_path.unlink(missing_ok=True)

    source_path.unlink()
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


def _translate(
    transcript: Transcript,
    config: KoffeeConfig,
    on_progress: Callable[[float], None] | None,
    output_dir: Path | None = None,
) -> Path:
    """Translates segments and writes an intermediate subtitle."""
    if config.provider == "whisper":
        segments = transcript.segments
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

    return generate_subtitles(config.subtitle_format, segments, output_dir)


def _translate_embedded_subtitles(
    input_path: Path | str,
    config: KoffeeConfig,
    on_progress: Callable[[float], None] | None,
) -> Path:
    """Extracts, translates, and routes one embedded subtitle track."""
    log.info("Extracting embedded subtitles from video.")

    with TemporaryDirectory(prefix="koffee-") as temporary_directory:
        working_directory = Path(temporary_directory)
        extracted_path = extract_subtitle_track(
            input_path,
            config.subtitle_track_index,
            output_dir=working_directory,
        )
        subtitle_path = _translate_subtitle_file(
            extracted_path,
            config,
            on_progress,
            output_dir=working_directory,
        )
        return _route_output(input_path, subtitle_path, config)


def _translate_subtitle_file(
    file_path: Path | str,
    config: KoffeeConfig,
    on_progress: Callable[[float], None] | None,
    output_dir: Path | None = None,
) -> Path:
    """Translates an existing subtitle file without ASR."""
    log.info("Detected subtitle file input, skipping transcription.")

    transcript: Transcript = Transcript(
        segments=parse_subtitle_file(file_path), language=config.source_language
    )
    return _translate_with_failure_context(
        transcript,
        config,
        on_progress,
        output_dir=output_dir,
    )


def _translate_with_failure_context(
    transcript: Transcript,
    config: KoffeeConfig,
    on_progress: Callable[[float], None] | None,
    output_dir: Path | None = None,
) -> Path:
    """Wraps recognized translation failures with source segments."""
    provider_errors = (
        AnthropicAPIError,
        GeminiAPIError,
        OpenAIError,
        TranslationIntegrityError,
    )
    try:
        return _translate(transcript, config, on_progress, output_dir)
    except provider_errors as exc:
        raise TranslationError(str(exc), transcript.segments) from exc


def _check_preconditions(input_path: Path | str, config: KoffeeConfig) -> None:
    """Checks all preconditions before processing begins."""
    # File Must Exist and Be a Valid File
    if not Path(input_path).exists() or not Path(input_path).is_file():
        error_message = "Input file is not valid or does not exist."
        log.error(error_message)
        raise InvalidVideoFileError(error_message)

    # File Extension Must Be a Supported Type
    suffix = Path(input_path).suffix.lower()
    allowed = SUPPORTED_EXTENSIONS | SUBTITLE_EXTENSIONS
    if suffix not in allowed:
        error_message = (
            f"Unsupported file type: {suffix!r}. "
            f"Supported extensions: {', '.join(sorted(allowed))}"
        )
        raise UnsupportedFileError(error_message)

    is_video = suffix in VIDEO_EXTENSIONS
    _check_subtitle_provider(suffix, config)

    # Embed and Use-Embedded-Subtitles Are Video-Only Options
    if config.embed != "none" and not is_video:
        error_message = "--embed is only supported for video file inputs."
        raise IncompatibleOptionsError(error_message)

    if config.use_embedded_subtitles and not is_video:
        error_message = (
            "--use-embedded-subtitles is only supported for video file inputs."
        )
        raise IncompatibleOptionsError(error_message)

    # ffmpeg and ffprobe Must Be Installed for Embed/Subtitle Extraction
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

    # LLM Backends Require an API Key
    if config.provider not in ("whisper", "ollama") and not config.api_key:
        error_message = (
            f"An API key is required when using the {config.provider} "
            "translation backend. Provide one with --api_key or set the appropriate "
            "environment variable."
        )
        raise MissingApiKeyError(error_message)

    # Output Path Must Not Already Exist (or Overwrite Must Be Set)
    has_embed = is_video and config.embed != "none"
    base_path = _get_output_path(
        input_path, config.output_dir, config.output_name, date_suffix=has_embed
    )
    output_path = (
        base_path if has_embed else base_path.with_suffix(f".{config.subtitle_format}")
    )
    _check_output_collision(output_path, config.overwrite)


def _check_subtitle_provider(
    suffix: str,
    config: KoffeeConfig,
) -> None:
    """Rejects Whisper for direct subtitle translation."""
    if suffix in SUBTITLE_EXTENSIONS and config.provider == "whisper":
        error_message = (
            "The whisper provider cannot translate "
            "subtitle files. Choose an LLM provider."
        )
        raise IncompatibleOptionsError(error_message)
