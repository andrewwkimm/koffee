"""Root CLI command and executable entry point."""

import logging
from pathlib import Path
from typing import Annotated

from cyclopts import Parameter

from koffee.cli.app import (
    _configure_logging,
    app,
    options_group,
)
from koffee.cli.batch import (
    _BatchItem,
    _print_dry_run,
    _resolve_paths,
    _run_batch,
    _validate_batch_options,
)
from koffee.cli.configuration import _resolve_config
from koffee.cli.embedded import _handle_embedded_subtitles


@app.default()
def cli(
    *file_path: Annotated[Path, Parameter()],
    compute_type: Annotated[
        str | None, Parameter(name=("--compute-type", "-c"))
    ] = None,
    device: Annotated[str | None, Parameter(name=("--device", "-d"))] = None,
    transcription_model: Annotated[
        str | None, Parameter(name=("--transcription-model", "-m"))
    ] = None,
    output_dir: Annotated[Path, Parameter(name=("--output-dir", "-o"))] | None = None,
    output_name: Annotated[str, Parameter(name=("--output-name", "-n"))] | None = None,
    source_language: Annotated[
        str | None, Parameter(name=("--source-language", "-s"))
    ] = None,
    target_language: Annotated[
        str | None, Parameter(name=("--target-language", "-t"))
    ] = None,
    subtitle_format: Annotated[
        str | None, Parameter(name=("--subtitle-format", "-f"))
    ] = None,
    embed: Annotated[str | None, Parameter(name=("--embed",))] = None,
    translator: Annotated[str | None, Parameter(name=("--translator",))] = None,
    translation_model: Annotated[str, Parameter(name=("--translation-model",))]
    | None = None,
    chunk_size: Annotated[int, Parameter(name=("--chunk-size",))] | None = None,
    context_size: Annotated[int, Parameter(name=("--context-size",))] | None = None,
    sleep_seconds: Annotated[int, Parameter(name=("--sleep",))] | None = None,
    prompt: Annotated[str, Parameter(name=("--prompt",))] | None = None,
    api_key: Annotated[str, Parameter(name=("--api-key",))] | None = None,
    on_translation_failure: Annotated[
        str | None, Parameter(name=("--on-translation-failure",))
    ] = None,
    config: Annotated[Path, Parameter(name=("--config",), group=options_group)]
    | None = None,
    vad_filter: Annotated[
        bool | None, Parameter(negative="--no-vad-filter", group=options_group)
    ] = None,
    dry_run: Annotated[
        bool | None, Parameter(name=("--dry-run",), group=options_group)
    ] = None,
    allow_mixed_translation: Annotated[
        bool | None,
        Parameter(
            name=("--allow-mixed-translation",),
            group=options_group,
        ),
    ] = None,
    overwrite: Annotated[
        bool | None, Parameter(name=("--overwrite",), group=options_group)
    ] = None,
    verbose: Annotated[
        bool, Parameter(name=("--verbose", "-v"), group=options_group)
    ] = False,
) -> None:
    """Automatic video translation and subtitling tool.

    Parameters
    ----------
    file_path: Path
        Path to the video, audio, or subtitle file
    compute_type: str
        Type to use for computation
    device: str
        Device to use for computation
    whisper_model: str
        The Whisper model instance to use
    output_dir: Path
        Directory for the output file
    output_name: str
        Name of the output file
    subtitle_format: str
        Format to use for the subtitles
    embed: str
        Subtitle embed mode: none (subtitle file only), soft (muxed track),
        or hard (burned into video frames). Only valid for video file inputs.
    source_language: str
        Source language of the subtitle file (default: auto)
    target_language: str
        Language to which the file should be translated
    provider: str
        The backend service to use for the translation
    llm_model: str
        The LLM model to use for translation
    prompt: str
        Custom system prompt for the LLM translation model
    config: Path
        Path to a koffee.toml configuration file
    api_key: str
        API key for an LLM service
    on_translation_failure: str
        What to do when LLM translation fails: prompt (default; ask y/n to save
        the raw transcription), save (save without asking), or abort (skip the
        save). When stdin is not a TTY, prompt falls back to save.
    vad_filter: bool
        Voice activity detection filtering during transcription (enabled by default;
        pass `--no-vad-filter` to disable)
    dry_run: bool
        Preview what would be done without running transcription or translation
    overwrite: bool
        Overwrite existing output files instead of raising an error
    verbose: bool
        Print debug log messages
    """
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    cli_args = {
        "api_key": api_key,
        "compute_type": compute_type,
        "device": device,
        "dry_run": dry_run,
        "transcription_model": transcription_model,
        "translation_model": translation_model,
        "chunk_size": chunk_size,
        "context_size": context_size,
        "sleep_seconds": sleep_seconds,
        "overwrite": overwrite,
        "allow_mixed_translation": allow_mixed_translation,
        "output_dir": output_dir,
        "output_name": output_name,
        "embed": embed,
        "source_language": source_language,
        "subtitle_format": subtitle_format,
        "target_language": target_language,
        "translator": translator,
        "prompt": prompt,
        "on_translation_failure": on_translation_failure,
        "vad_filter": vad_filter,
    }
    config = _resolve_config(config, cli_args)

    resolved_paths = _resolve_paths(file_path)
    _validate_batch_options(resolved_paths, config)
    batch_items = [
        _BatchItem(
            input_path=input_path,
            config=_handle_embedded_subtitles(input_path, config),
        )
        for input_path in resolved_paths
    ]

    if config.dry_run:
        _print_dry_run(batch_items)
        return

    _run_batch(batch_items)


def main() -> None:
    """Configures and runs the command-line application."""
    _configure_logging()
    app()
