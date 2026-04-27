"""CLI command implementations."""

import logging
import shutil
import subprocess
from pathlib import Path
from typing import Annotated

from cyclopts import Parameter, validators
from rich.console import Console
from rich.progress import Progress
from rich.table import Table

from koffee import asr
from koffee.api import SUBTITLE_EXTENSIONS, SUPPORTED_EXTENSIONS, _write_output, run
from koffee.cli.app import app, defaults, log, options_group
from koffee.cli.embedded import _handle_embedded_subtitles
from koffee.cli.progress import _create_progress_bar, _make_progress_callback
from koffee.embed import embed_subtitles
from koffee.exceptions import KoffeeError, TranslationError
from koffee.schemas.config import (
    CONFIG_SEARCH_PATHS,
    LANGUAGE_CODES,
    LANGUAGE_NAMES,
    KoffeeConfig,
    load_config_file,
)
from koffee.subtitle import generate_subtitles, get_subtitle_tracks, parse_subtitle_file


@app.default()
def cli(
    *file_path: Annotated[Path, Parameter(validator=validators.Path(exists=True))],
    compute_type: Annotated[
        str, Parameter(name=("--compute-type", "-c"))
    ] = defaults.compute_type,
    device: Annotated[str, Parameter(name=("--device", "-d"))] = defaults.device,
    whisper_model: Annotated[
        str, Parameter(name=("--whisper-model", "-m"))
    ] = defaults.whisper_model,
    output_dir: Annotated[Path, Parameter(name=("--output-dir", "-o"))] | None = None,
    output_name: Annotated[str, Parameter(name=("--output-name", "-n"))] | None = None,
    source_language: Annotated[
        str, Parameter(name=("--source-language", "-s"))
    ] = defaults.source_language,
    target_language: Annotated[
        str, Parameter(name=("--target-language", "-t"))
    ] = defaults.target_language,
    subtitle_format: Annotated[
        str, Parameter(name=("--subtitle-format", "-f"))
    ] = defaults.subtitle_format,
    embed: Annotated[str, Parameter(name=("--embed",))] = defaults.embed,
    provider: Annotated[str, Parameter(name=("--provider",))] = defaults.provider,
    llm_model: Annotated[str, Parameter(name=("--llm-model",))] | None = None,
    chunk_size: Annotated[int, Parameter(name=("--chunk-size",))] | None = None,
    context_size: Annotated[int, Parameter(name=("--context-size",))] | None = None,
    sleep_requests: Annotated[int, Parameter(name=("--sleep-requests",))] | None = None,
    prompt: Annotated[str, Parameter(name=("--prompt",))] | None = None,
    api_key: Annotated[str, Parameter(name=("--api-key",))] | None = None,
    on_translation_failure: Annotated[
        str, Parameter(name=("--on-translation-failure",))
    ] = defaults.on_translation_failure,
    config: Annotated[Path, Parameter(name=("--config",), group=options_group)]
    | None = None,
    vad_filter: Annotated[
        bool, Parameter(negative="--no-vad-filter", group=options_group)
    ] = True,
    dry_run: Annotated[
        bool, Parameter(name=("--dry-run",), group=options_group)
    ] = False,
    overwrite: Annotated[
        bool, Parameter(name=("--overwrite",), group=options_group)
    ] = False,
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
        "whisper_model": whisper_model,
        "llm_model": llm_model,
        "chunk_size": chunk_size,
        "context_size": context_size,
        "sleep_requests": sleep_requests,
        "overwrite": overwrite,
        "output_dir": output_dir,
        "output_name": output_name,
        "embed": embed,
        "source_language": source_language,
        "subtitle_format": subtitle_format,
        "target_language": target_language,
        "provider": provider,
        "prompt": prompt,
        "on_translation_failure": on_translation_failure,
        "vad_filter": vad_filter,
    }
    default_config = KoffeeConfig().model_dump()
    cli_overrides = {k: v for k, v in cli_args.items() if v != default_config.get(k)}
    file_config = load_config_file(config)
    resolved_config = {**default_config, **file_config, **cli_overrides}
    config = KoffeeConfig(**resolved_config)

    resolved_paths = _resolve_paths(file_path)

    for video_path in resolved_paths:
        config = _handle_embedded_subtitles(video_path, config)

    if config.dry_run:
        _print_dry_run(resolved_paths, config)
        return

    total = len(resolved_paths)
    failed = []
    with _create_progress_bar() as progress:
        for i, video_path in enumerate(resolved_paths, 1):
            if total > 1:
                log.info(f"[{i}/{total}] Processing {video_path.name}")
            try:
                _translate_with_progress(video_path, config, progress)
            except (
                FileExistsError,
                FileNotFoundError,
                KoffeeError,
                subprocess.CalledProcessError,
                subprocess.TimeoutExpired,
            ) as exc:
                log.error(f"Failed to process {video_path.name}: {exc}")
                failed.append(video_path)

    if total > 1:
        succeeded = total - len(failed)
        log.info(f"Batch complete: {succeeded}/{total} succeeded.")
        if failed:
            for path in failed:
                log.info(f"  failed: {path.name}")


def _print_dry_run(resolved_paths: list[Path], config: KoffeeConfig) -> None:
    """Prints a preview of what would be done without running anything."""
    log.info("[dry-run] Would process the following files:")
    for path in resolved_paths:
        suffix = path.suffix.lower()
        if suffix in SUBTITLE_EXTENSIONS:
            mode = "subtitle translation (skip ASR)"
        elif config.use_embedded_subtitles:
            mode = "embedded subtitle extraction + translation"
        else:
            mode = f"ASR ({config.whisper_model}) + translation ({config.provider})"
        log.info(f"  {path.name} -> {mode}")

    log.info(f"[dry-run] Target language: {config.target_language}")
    log.info(f"[dry-run] Output format: {config.subtitle_format}")
    if config.embed != "none":
        log.info(f"[dry-run] Subtitles will be embedded into video ({config.embed})")


def _resolve_paths(file_path: tuple) -> list[Path]:
    """Resolves glob patterns, directories, and files into a flat list of paths."""
    resolved_paths = []
    for pattern in file_path:
        path = Path(pattern)
        if path.is_dir():
            resolved_paths.extend(
                sorted(
                    p
                    for p in path.iterdir()
                    if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
                )
            )
        elif path.exists():
            resolved_paths.append(path)
        else:
            matches = sorted(Path.cwd().glob(str(pattern)))
            if matches:
                resolved_paths.extend(matches)
            else:
                resolved_paths.append(path)

    return resolved_paths


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
        has_translate_step = config.provider != "whisper"
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

        try:
            run(
                input_path=video_path,
                config=config,
                on_asr_progress=on_asr_progress,
                on_translate_progress=translate_callback,
            )
        except TranslationError as exc:
            log.error(f"Translation failed: {exc}")
            answer = input("Save transcription as subtitles for manual retry? [y/N] ")
            if answer.strip().lower() == "y":
                raw_path = generate_subtitles(config.subtitle_format, exc.segments)
                output_path = _write_output(
                    raw_path,
                    video_path,
                    config.subtitle_format,
                    config.output_dir,
                    config.output_name,
                    config.overwrite,
                )
                log.info(
                    f"Transcription saved to {output_path}. "
                    f"Retry: koffee {output_path} --provider=<provider>"
                )
            else:
                raise


@app.command()
def convert(
    file_path: Annotated[Path, Parameter(validator=validators.Path(exists=True))],
    subtitle_format: Annotated[str, Parameter(name=("--format", "-f"))] = "vtt",
    output_dir: Annotated[Path, Parameter(name=("--output-dir", "-o"))] | None = None,
    output_name: Annotated[str, Parameter(name=("--output-name", "-n"))] | None = None,
    overwrite: Annotated[
        bool, Parameter(name=("--overwrite",), group=options_group)
    ] = False,
) -> None:
    """Convert a subtitle file between formats (SRT, VTT, ASS).

    Parameters
    ----------
    file_path: Path
        Path to the subtitle file
    subtitle_format: str
        Target subtitle format (srt, vtt, or ass)
    output_dir: Path
        Directory for the output file
    output_name: str
        Name of the output file
    overwrite: bool
        Overwrite existing output files instead of raising an error
    """
    segments = parse_subtitle_file(file_path)
    out_dir = output_dir if output_dir is not None else file_path.parent
    subtitle_path = generate_subtitles(subtitle_format, segments, out_dir)

    target_path = _write_output(
        subtitle_path,
        file_path,
        subtitle_format,
        output_dir,
        output_name,
        overwrite,
    )
    log.info(f"Converted {file_path.name} to {target_path}")


@app.command()
def embed(
    video_path: Annotated[Path, Parameter(validator=validators.Path(exists=True))],
    subtitle_path: Annotated[Path, Parameter(validator=validators.Path(exists=True))],
    output_path: Annotated[Path, Parameter(name=("--output", "-o"))] | None = None,
    mode: Annotated[str, Parameter(name=("--mode", "-m"))] = "soft",
    overwrite: Annotated[
        bool, Parameter(name=("--overwrite",), group=options_group)
    ] = False,
) -> None:
    """Embed subtitles into a video without transcription or translation.

    Parameters
    ----------
    video_path: Path
        Path to the video file
    subtitle_path: Path
        Path to the subtitle file
    output_path: Path
        Path for the output video file
    mode: str
        Embed mode: soft (muxed track) or hard (burned into video frames)
    overwrite: bool
        Overwrite existing output files instead of raising an error
    """
    if output_path is None:
        output_path = video_path.with_stem(f"{video_path.stem}_embed")

    if output_path.exists() and not overwrite:
        error_message = (
            f"Output file already exists: {output_path}. Use --overwrite to replace it."
        )
        raise FileExistsError(error_message)

    result = embed_subtitles(subtitle_path, video_path, output_path, mode=mode)
    log.info(f"Output saved to {result}")


@app.command()
def info() -> None:
    """Display system information for debugging."""
    import sys  # noqa: PLC0415

    log.info("[koffee info]")

    import koffee  # noqa: PLC0415

    log.info(f"  koffee: {koffee.__version__}")
    log.info(f"  python: {sys.version.split()[0]}")

    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
        version_line = result.stdout.split("\n")[0]
        log.info(f"  ffmpeg: {version_line}")
    else:
        log.info("  ffmpeg: not found")

    ffprobe_path = shutil.which("ffprobe")
    log.info(f"  ffprobe: {'found' if ffprobe_path else 'not found'}")

    try:
        import torch  # noqa: PLC0415

        cuda_available = torch.cuda.is_available()
        device_name = torch.cuda.get_device_name(0) if cuda_available else "N/A"
        log.info(f"  torch: {torch.__version__}")
        log.info(f"  CUDA: {'available' if cuda_available else 'not available'}")
        if cuda_available:
            log.info(f"  GPU: {device_name}")
            vram_bytes = torch.cuda.get_device_properties(0).total_memory
            log.info(f"  VRAM: {vram_bytes / 1024**3:.1f} GB")
    except ImportError:
        log.info("  torch: not installed")

    try:
        import faster_whisper  # noqa: PLC0415

        log.info(f"  faster-whisper: {faster_whisper.__version__}")
    except ImportError:
        log.info("  faster-whisper: not installed")

    config = KoffeeConfig(**load_config_file())
    log.info(f"  default whisper model: {config.whisper_model}")
    log.info(f"  default backend: {config.provider}")
    log.info(f"  config file: {_find_config_path() or 'none'}")


def _find_config_path() -> Path | None:
    """Returns the path to the active config file, or None."""
    for path in CONFIG_SEARCH_PATHS:
        if path.is_file():
            return path
    return None


@app.command()
def languages() -> None:
    """List all supported language codes."""
    num_columns = 4
    codes = sorted(LANGUAGE_CODES - {"auto"})
    entries = [f"{code} ({LANGUAGE_NAMES.get(code, code)})" for code in codes]

    table = Table(show_header=False, box=None, pad_edge=False, expand=True)
    for _ in range(num_columns):
        table.add_column()

    for i in range(0, len(entries), num_columns):
        row = entries[i : i + num_columns]
        row += [""] * (num_columns - len(row))
        table.add_row(*row)

    console = Console()
    console.print(table)
    console.print(f"\n[bold]{len(codes)}[/bold] supported languages")


@app.command()
def tracks(
    file_path: Annotated[Path, Parameter(validator=validators.Path(exists=True))],
) -> None:
    """List embedded subtitle tracks in a video file."""
    track_list = get_subtitle_tracks(file_path)

    if not track_list:
        log.info(f"No subtitle tracks found in {file_path.name}.")
        return

    log.info(f"Subtitle tracks in {file_path.name}:")
    for i, track in enumerate(track_list):
        tags = track.get("tags", {})
        language = tags.get("language", "unknown")
        title = tags.get("title", "")
        label = f"  [{i}] {language}"
        if title:
            label += f" — {title}"
        log.info(label)


@app.command()
def transcribe(
    file_path: Annotated[Path, Parameter(validator=validators.Path(exists=True))],
    compute_type: Annotated[
        str, Parameter(name=("--compute-type", "-c"))
    ] = defaults.compute_type,
    device: Annotated[str, Parameter(name=("--device", "-d"))] = defaults.device,
    whisper_model: Annotated[
        str, Parameter(name=("--whisper-model", "-m"))
    ] = defaults.whisper_model,
    output_dir: Annotated[Path, Parameter(name=("--output-dir", "-o"))] | None = None,
    output_name: Annotated[str, Parameter(name=("--output-name", "-n"))] | None = None,
    subtitle_format: Annotated[
        str, Parameter(name=("--subtitle-format", "-f"))
    ] = defaults.subtitle_format,
    vad_filter: Annotated[
        bool, Parameter(negative="--no-vad-filter", group=options_group)
    ] = True,
    overwrite: Annotated[
        bool, Parameter(name=("--overwrite",), group=options_group)
    ] = False,
) -> None:
    """Transcribe audio to subtitles without translation.

    Parameters
    ----------
    file_path: Path
        Path to the video or audio file
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
    vad_filter: bool
        Voice activity detection filtering during transcription (enabled by default;
        pass `--no-vad-filter` to disable)
    overwrite: bool
        Overwrite existing output files instead of raising an error
    """
    with _create_progress_bar() as progress:
        asr_task = progress.add_task("Transcribing", total=100)

        transcript = asr.transcribe(
            str(file_path),
            compute_type,
            device,
            whisper_model,
            "whisper",
            on_progress=_make_progress_callback(progress, asr_task),
            vad_filter=vad_filter,
        )

    segments = transcript["segments"]
    out_dir = output_dir if output_dir is not None else file_path.parent
    subtitle_path = generate_subtitles(subtitle_format, segments, out_dir)

    target_path = _write_output(
        subtitle_path,
        file_path,
        subtitle_format,
        output_dir,
        output_name,
        overwrite,
    )
    log.info(f"Output saved to {target_path}")


app["info"].sort_key = 0
app["languages"].sort_key = 1
app["tracks"].sort_key = 2
app["transcribe"].sort_key = 3
app["convert"].sort_key = 4
app["embed"].sort_key = 5


def main() -> None:
    """Wraps app() so that it is accessible to poetry."""
    app()
