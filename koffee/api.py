"""The koffee API."""

import logging
import shutil
from collections.abc import Callable
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory
from typing import Any

from anthropic import APIError as AnthropicAPIError
from google.genai.errors import APIError as GeminiAPIError
from openai import OpenAIError

from koffee.asr import transcribe
from koffee.embed import embed_subtitles, validate_embedding
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
from koffee.job import JobStore
from koffee.media import (
    AUDIO_EXTENSIONS,
    SUPPORTED_EXTENSIONS,
    VIDEO_EXTENSIONS,
    OutputPolicy,
    classify_media,
    resolve_output_path,
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


def run(
    input_path: Path | str,
    config: KoffeeConfig | None = None,
    on_asr_progress: Callable[[float], None] | None = None,
    on_translate_progress: Callable[[float], None] | None = None,
    job: JobStore | None = None,
    **kwargs: Any,
) -> Path:
    """Processes one media or subtitle file into translated output."""
    log.info("Translating file...")

    if config is None:
        config = KoffeeConfig(**kwargs)
    else:
        config = KoffeeConfig(
            **{
                **config.model_dump(),
                **kwargs,
            }
        )

    _check_preconditions(input_path, config)
    output_path = _resolve_output_path(input_path, config)
    if config.dry_run:
        return output_path

    current_job = job or JobStore.open(input_path, config)

    suffix = Path(input_path).suffix.lower()
    if suffix in SUBTITLE_EXTENSIONS:
        subtitle_path = _translate_subtitle_file(
            input_path,
            config,
            on_translate_progress,
            job=current_job,
        )
    elif config.use_embedded_subtitles:
        output_path = _translate_embedded_subtitles(
            input_path,
            config,
            on_translate_progress,
            job=current_job,
        )
        current_job.delete()
        return output_path
    else:
        transcript = current_job.load_transcript()
        if transcript is None:
            task = "translate" if config.translator == "whisper" else "transcribe"
            transcript = transcribe(
                str(input_path),
                compute_type=config.compute_type,
                device=config.device,
                model=config.transcription_model,
                task=task,
                on_progress=on_asr_progress,
                vad_filter=config.vad_filter,
                language=_resolve_asr_language(config.source_language),
            )
            current_job.save_transcript(transcript)
        elif on_asr_progress is not None:
            # A resumed transcript skips ASR, so the caller's progress
            # display would otherwise never advance past transcription.
            on_asr_progress(1.0)

        subtitle_path = _translate_with_failure_context(
            transcript,
            config,
            on_translate_progress,
            job=current_job,
        )

    output_path = _route_output(
        input_path,
        subtitle_path,
        config,
    )
    current_job.delete()
    return output_path


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

    output_path = _resolve_output_path(input_path, config)

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
            subtitle_format=config.subtitle_format,
            output_dir=output_path.parent,
            output_name=output_path.name,
            overwrite=config.overwrite,
        )

    return result_path


def _write_embedded_video(
    subtitle_path: Path,
    input_path: Path,
    output_path: Path,
    embed_mode: str = "soft",
    language: str = "en",
    *,
    delete_subtitle: bool = True,
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

    if delete_subtitle:
        subtitle_path.unlink()
    log.info("Finished processing video!")
    return output_path


def _write_output(
    source_path: Path,
    input_path: Path | str,
    *,
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
    target_path = (
        base_path
        if output_name is not None
        else base_path.with_suffix(f".{subtitle_format}")
    )

    try:
        _check_output_collision(target_path, overwrite)
    except FileExistsError:
        source_path.unlink(missing_ok=True)
        raise

    target_path.parent.mkdir(parents=True, exist_ok=True)
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
    """Returns a compatibility base path without clock-dependent naming."""
    del date_suffix
    file_path = Path(input_path)
    file_dir = output_dir if output_dir is not None else file_path.parent
    file_name = output_name if output_name is not None else file_path.stem
    output_filename = (
        file_name if output_name is not None else file_name + file_path.suffix
    )
    return file_dir / output_filename


def _resolve_output_path(
    input_path: Path | str,
    config: KoffeeConfig,
) -> Path:
    """Returns the deterministic translated publication path."""
    media = classify_media(input_path)
    embed_mode = config.embed if media is not None and media.kind == "video" else "none"
    return resolve_output_path(
        OutputPolicy(
            input_path=Path(input_path),
            output_dir=config.output_dir,
            output_name=config.output_name,
            target_language=config.target_language,
            subtitle_format=config.subtitle_format,
            embed_mode=embed_mode,
        )
    )


def _translate(
    transcript: Transcript,
    config: KoffeeConfig,
    on_progress: Callable[[float], None] | None,
    output_dir: Path | None = None,
    job: JobStore | None = None,
) -> Path:
    """Translates segments and writes an intermediate subtitle."""
    if config.translator == "whisper":
        segments = transcript.segments
    else:
        api_key = (
            config.api_key.get_secret_value() if config.api_key is not None else None
        )
        segments = translate(
            transcript,
            config.target_language,
            api_key=api_key,
            on_progress=on_progress,
            translation_model=config.translation_model,
            prompt=config.prompt,
            translator=config.translator,
            chunk_size=config.chunk_size,
            context_size=config.context_size,
            sleep_seconds=config.sleep_seconds,
            job=job,
            allow_mixed_translation=config.allow_mixed_translation,
        )

    return generate_subtitles(
        config.subtitle_format,
        segments,
        output_dir,
    )


def _translate_embedded_subtitles(
    input_path: Path | str,
    config: KoffeeConfig,
    on_progress: Callable[[float], None] | None,
    job: JobStore | None = None,
) -> Path:
    """Extracts, translates, and routes one embedded track."""
    log.info("Extracting embedded subtitles from video.")

    with TemporaryDirectory(prefix="koffee-") as temporary_directory:
        working_directory = Path(temporary_directory)
        extracted_path = extract_subtitle_track(
            input_path,
            subtitle_ordinal=config.subtitle_track,
            output_dir=working_directory,
        )
        subtitle_path = _translate_subtitle_file(
            extracted_path,
            config,
            on_progress,
            output_dir=working_directory,
            job=job,
        )
        return _route_output(
            input_path,
            subtitle_path,
            config,
        )


def _translate_subtitle_file(
    file_path: Path | str,
    config: KoffeeConfig,
    on_progress: Callable[[float], None] | None,
    output_dir: Path | None = None,
    job: JobStore | None = None,
) -> Path:
    """Translates an existing subtitle file without ASR."""
    log.info("Detected subtitle file input, skipping transcription.")
    transcript = Transcript(
        segments=parse_subtitle_file(file_path),
        language=config.source_language,
    )
    return _translate_with_failure_context(
        transcript,
        config,
        on_progress,
        output_dir=output_dir,
        job=job,
    )


def _translate_with_failure_context(
    transcript: Transcript,
    config: KoffeeConfig,
    on_progress: Callable[[float], None] | None,
    output_dir: Path | None = None,
    job: JobStore | None = None,
) -> Path:
    """Wraps recognized failures with source segments."""
    provider_errors = (
        AnthropicAPIError,
        GeminiAPIError,
        OpenAIError,
        TranslationIntegrityError,
    )
    try:
        return _translate(
            transcript,
            config,
            on_progress,
            output_dir,
            job,
        )
    except provider_errors as error:
        raise TranslationError(
            str(error),
            transcript.segments,
        ) from error


def _check_preconditions(
    input_path: Path | str,
    config: KoffeeConfig,
) -> None:
    """Checks all preconditions before processing begins."""
    input_file = Path(input_path)
    if not input_file.exists() or not input_file.is_file():
        error_message = "Input file is not valid or does not exist."
        log.error(error_message)
        raise InvalidVideoFileError(error_message)

    suffix = input_file.suffix.lower()
    allowed_extensions = SUPPORTED_EXTENSIONS | SUBTITLE_EXTENSIONS
    if suffix not in allowed_extensions:
        error_message = (
            f"Unsupported file type: {suffix!r}. "
            f"Supported extensions: "
            f"{', '.join(sorted(allowed_extensions))}"
        )
        raise UnsupportedFileError(error_message)

    _check_subtitle_provider(suffix, config)
    _check_media_options(
        input_file,
        config,
        is_video=suffix in VIDEO_EXTENSIONS,
    )

    if config.translator not in ("whisper", "ollama") and not config.api_key:
        error_message = (
            f"An API key is required when using the "
            f"{config.translator} translation backend. Provide one with "
            "--api-key or set the appropriate environment variable."
        )
        raise MissingApiKeyError(error_message)

    output_path = _resolve_output_path(input_file, config)
    _check_distinct_output(input_file, output_path)
    _check_output_collision(output_path, config.overwrite)


def _check_distinct_output(input_path: Path | str, output_path: Path) -> None:
    """Rejects output paths that identify the input file."""
    input_file = Path(input_path)
    try:
        aliases_input = output_path.exists() and input_file.samefile(output_path)
    except OSError:
        aliases_input = False
    if aliases_input or input_file.resolve() == output_path.resolve():
        raise IncompatibleOptionsError("Output file must differ from the input file.")


def _check_subtitle_provider(
    suffix: str,
    config: KoffeeConfig,
) -> None:
    """Rejects Whisper for direct subtitle translation."""
    if suffix in SUBTITLE_EXTENSIONS and config.translator == "whisper":
        error_message = (
            "The whisper provider cannot translate "
            "subtitle files. Choose an LLM provider."
        )
        raise IncompatibleOptionsError(error_message)


def _check_media_options(
    input_path: Path,
    config: KoffeeConfig,
    *,
    is_video: bool,
) -> None:
    """Checks options that require video media or FFmpeg."""
    _check_video_only_options(config, is_video=is_video)

    needs_ffmpeg = config.embed != "none" or config.use_embedded_subtitles
    if not needs_ffmpeg:
        return

    if shutil.which("ffmpeg") is None:
        error_message = (
            "ffmpeg was not found on PATH. Install ffmpeg to use "
            "--embed or --use-embedded-subtitles."
        )
        raise MissingDependencyError(error_message)

    if config.use_embedded_subtitles:
        _check_embedded_subtitle_track(
            input_path,
            config.subtitle_track,
        )

    if config.embed != "none":
        validate_embedding(
            _resolve_output_path(input_path, config),
            config.embed,
        )


def _check_video_only_options(
    config: KoffeeConfig,
    *,
    is_video: bool,
) -> None:
    """Checks that video-only options receive video input."""
    if config.embed != "none" and not is_video:
        error_message = "--embed is only supported for video file inputs."
        raise IncompatibleOptionsError(error_message)

    if config.use_embedded_subtitles and not is_video:
        error_message = (
            "--use-embedded-subtitles is only supported for video file inputs."
        )
        raise IncompatibleOptionsError(error_message)


def _check_embedded_subtitle_track(
    input_path: Path,
    subtitle_ordinal: int,
) -> None:
    """Checks that one requested text subtitle track is available."""
    if shutil.which("ffprobe") is None:
        error_message = (
            "ffprobe was not found on PATH. Install ffmpeg to use "
            "--use-embedded-subtitles."
        )
        raise MissingDependencyError(error_message)

    subtitle_tracks = get_subtitle_tracks(input_path)
    if not subtitle_tracks:
        error_message = f"No text subtitle tracks found in {input_path}."
        raise IncompatibleOptionsError(error_message)

    available_ordinals = {track.subtitle_ordinal for track in subtitle_tracks}
    if subtitle_ordinal not in available_ordinals:
        error_message = (
            f"Subtitle track ordinal {subtitle_ordinal} is unavailable. "
            f"Available text subtitle ordinals: "
            f"{sorted(available_ordinals)}."
        )
        raise IncompatibleOptionsError(error_message)
