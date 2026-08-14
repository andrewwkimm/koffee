"""Batch planning, execution, and failure recovery."""

import subprocess
import sys
from pathlib import Path

from pydantic import BaseModel, ConfigDict
from rich.progress import Progress
from rich.prompt import Confirm

from koffee.api import (
    SUPPORTED_EXTENSIONS,
    _write_output,
    run,
)
from koffee.cli.app import log
from koffee.cli.progress import (
    _create_progress_bar,
    _make_progress_callback,
)
from koffee.exceptions import (
    IncompatibleOptionsError,
    KoffeeError,
    TranslationError,
    TranslationPausedError,
)
from koffee.schemas.config import KoffeeConfig
from koffee.subtitle import (
    SUBTITLE_EXTENSIONS,
    generate_subtitles,
)


class _BatchItem(BaseModel):
    """Binds one input path to its independently resolved configuration."""

    model_config = ConfigDict(frozen=True)

    input_path: Path
    config: KoffeeConfig


def _validate_batch_options(
    input_paths: list[Path],
    config: KoffeeConfig,
) -> None:
    """Rejects options that collide across inputs."""
    if len(input_paths) > 1 and config.output_name is not None:
        error_message = "--output-name cannot be used with multiple input files."
        raise IncompatibleOptionsError(error_message)


def _print_dry_run(batch_items: list[_BatchItem]) -> None:
    """Prints the independently resolved operation for each input."""
    log.info("[dry-run] Would process the following files:")
    for item in batch_items:
        path = item.input_path
        config = item.config
        suffix = path.suffix.lower()
        if suffix in SUBTITLE_EXTENSIONS:
            mode = "subtitle translation (skip ASR)"
        elif config.use_embedded_subtitles:
            mode = "embedded subtitle extraction + translation"
        else:
            mode = (
                f"ASR ({config.transcription_model}) "
                f"+ translation ({config.translator})"
            )
        if config.embed != "none":
            mode = f"{mode} + subtitles embedded into video ({config.embed})"
        log.info(f"  {path.name} -> {mode}")


def _resolve_paths(
    file_path: tuple[Path, ...],
) -> list[Path]:
    """Resolves supported files, directories, and globs."""
    input_extensions = SUPPORTED_EXTENSIONS | SUBTITLE_EXTENSIONS
    resolved_paths = []

    for pattern in file_path:
        path = Path(pattern)
        if path.is_dir():
            resolved_paths.extend(
                sorted(
                    candidate
                    for candidate in path.iterdir()
                    if candidate.is_file()
                    and candidate.suffix.lower() in input_extensions
                )
            )
        elif path.exists():
            resolved_paths.append(path)
        else:
            matches = sorted(
                candidate
                for candidate in Path.cwd().glob(str(pattern))
                if candidate.is_file() and candidate.suffix.lower() in input_extensions
            )
            if not matches:
                raise FileNotFoundError(f"No such file or pattern: {pattern}")
            resolved_paths.extend(matches)

    return resolved_paths


def _run_batch(
    batch_items: list[_BatchItem],
) -> None:
    """Processes configured inputs without aborting."""
    total = len(batch_items)
    failed = []

    with _create_progress_bar() as progress:
        for position, item in enumerate(
            batch_items,
            start=1,
        ):
            input_path = item.input_path
            config = item.config

            if total > 1:
                log.info(f"[{position}/{total}] Processing {input_path.name}")

            try:
                _translate_with_progress(
                    input_path,
                    config,
                    progress,
                )
            except TranslationPausedError as error:
                log.error(f"Translation paused for {input_path.name}: {error}")
                failed.append(input_path)
            except TranslationError as error:
                handled = _handle_translation_failure(
                    error,
                    input_path,
                    config,
                    progress,
                )
                if not handled:
                    failed.append(input_path)
            except (
                FileExistsError,
                FileNotFoundError,
                KoffeeError,
                subprocess.CalledProcessError,
                subprocess.TimeoutExpired,
            ) as error:
                log.error(f"Failed to process {input_path.name}: {error}")
                failed.append(input_path)

    if total > 1:
        succeeded = total - len(failed)
        log.info(f"Batch complete: {succeeded}/{total} succeeded.")
        for failed_path in failed:
            log.info(f"  failed: {failed_path.name}")


def _handle_translation_failure(
    exc: TranslationError,
    video_path: Path,
    config: KoffeeConfig,
    progress: Progress,
) -> bool:
    """Decides whether to save the raw transcription after a translation failure.

    Returns True if the failure was handled (saved or explicitly skipped) so the
    batch can continue cleanly; returns False to mark the file as failed.
    """
    log.error(f"Translation failed: {exc}")

    decision = config.on_translation_failure
    if decision == "prompt" and not sys.stdin.isatty():
        log.info("stdin is not a TTY; saving transcription instead of prompting.")
        decision = "save"

    if decision == "abort":
        return False

    if decision == "prompt":
        progress.stop()
        save = Confirm.ask(
            "Save transcription as subtitles for manual retry?",
            default=True,
            console=progress.console,
        )
        progress.start()
        if not save:
            return False

    _save_raw_transcription(exc, video_path, config)
    return True


def _save_raw_transcription(
    exc: TranslationError,
    video_path: Path,
    config: KoffeeConfig,
) -> None:
    """Writes the raw (untranslated) transcript to disk for manual retry."""
    raw_path = generate_subtitles(config.subtitle_format, exc.segments)
    output_path = _write_output(
        raw_path,
        video_path,
        subtitle_format=config.subtitle_format,
        output_dir=config.output_dir,
        output_name=config.output_name,
        overwrite=config.overwrite,
    )
    log.info(
        f"Transcription saved to {output_path}. "
        f"Retry: koffee {output_path} --provider=<provider>"
    )


def _translate_with_progress(
    video_path: Path,
    config: KoffeeConfig,
    progress: Progress,
) -> None:
    """Runs translation for a single file with ASR and translation progress bars."""
    skip_asr = (
        config.use_embedded_subtitles
        or video_path.suffix.lower() in SUBTITLE_EXTENSIONS
    )

    if skip_asr:
        translate_task = progress.add_task("Translating", total=100)
        run(
            input_path=video_path,
            config=config,
            on_translate_progress=_make_progress_callback(progress, translate_task),
        )
    else:
        has_translate_step = config.translator != "whisper"
        asr_task = progress.add_task("Transcribing", total=100)
        translate_task = None
        translate_callback = None

        if has_translate_step:
            translate_task = progress.add_task(
                "Translating", total=100, start=False, visible=False
            )
            translate_callback = _make_progress_callback(progress, translate_task)

        def on_asr_progress(ratio: float) -> None:
            progress.update(asr_task, completed=ratio * 100)
            if ratio >= 1.0:
                progress.stop_task(asr_task)
                if translate_task is not None:
                    progress.update(translate_task, visible=True)
                    progress.start_task(translate_task)

        run(
            input_path=video_path,
            config=config,
            on_asr_progress=on_asr_progress,
            on_translate_progress=translate_callback,
        )
