"""The koffee CLI."""

import logging
import shutil
import subprocess
from pathlib import Path
from typing import Annotated

from cyclopts import App, Group, Parameter, validators
from rich.logging import RichHandler
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)

from koffee.data.config import CONFIG_SEARCH_PATHS, KoffeeConfig, load_config_file
from koffee.translate import SUBTITLE_EXTENSIONS, SUPPORTED_EXTENSIONS, translate
from koffee.utils import get_subtitle_tracks

logging.basicConfig(
    level=logging.INFO, format="%(message)s", datefmt="[%X]", handlers=[RichHandler()]
)

log = logging.getLogger(__name__)

app = App(
    default_parameter=Parameter(negative=""),
    group_parameters=Group("Parameters", sort_key=1),
    name="koffee",
    version_flags=["--version", "-v"],
)

options_group = Group("Options", sort_key=2)

app["--help"].group = options_group
app["--version"].group = options_group

options = KoffeeConfig(**load_config_file())


def _create_progress_bar() -> Progress:
    """Creates a rich progress bar for tracking transcription and translation."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        TextColumn("{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
    )


def _make_progress_callback(progress: Progress, task_id) -> callable:
    """Returns a callback that updates a progress bar given a 0.0-1.0 ratio."""

    def callback(ratio: float) -> None:
        progress.update(task_id, completed=ratio * 100)

    return callback


@app.default()
def cli(
    *file_path: Annotated[Path, Parameter(validator=validators.Path(exists=True))],
    compute_type: Annotated[
        str, Parameter(name=("--compute-type", "-c"))
    ] = options.compute_type,
    device: Annotated[str, Parameter(name=("--device", "-d"))] = options.device,
    model: Annotated[str, Parameter(name=("--model", "-m"))] = options.model,
    output_dir: Annotated[Path, Parameter(name=("--output_dir", "-o"))] | None = None,
    output_name: Annotated[str, Parameter(name=("--output_name", "-n"))] | None = None,
    source_lang: Annotated[
        str, Parameter(name=("--source_lang", "-sl"))
    ] = options.source_language,
    target_lang: Annotated[
        str, Parameter(name=("--target_lang", "-t"))
    ] = options.target_language,
    subtitle_format: Annotated[
        str, Parameter(name=("--subtitle_format", "-sf"))
    ] = options.subtitle_format,
    overlay: Annotated[
        str, Parameter(name=("--overlay",), group=options_group)
    ] = options.overlay,
    translation_backend: Annotated[
        str, Parameter(name=("--translation_backend", "-tb"))
    ] = options.translation_backend,
    api_key: Annotated[str, Parameter(name=("--api_key", "-ak"), group=options_group)]
    | None = None,
    dry_run: Annotated[
        bool, Parameter(name=("--dry-run",), group=options_group)
    ] = False,
    overwrite: Annotated[
        bool, Parameter(name=("--overwrite",), group=options_group)
    ] = False,
    verbose: Annotated[
        bool, Parameter(name=("--verbose", "-V"), group=options_group)
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
    model: str
        The Whisper model instance to use
    output_dir: Path
        Directory for the output file
    output_name: str
        Name of the output file
    subtitle_format: str
        Format to use for the subtitles
    overlay: str
        Subtitle overlay mode: none (subtitle file only), soft (muxed track),
        or hard (burned into video frames). Only valid for video file inputs.
    source_language: str
        Source language of the subtitle file (default: auto)
    target_language: str
        Language to which the file should be translated
    translation_backend: str
        The backend service to use for the translation
    api_key: str
        API key for an LLM service
    dry_run: bool
        Preview what would be done without running transcription or translation
    overwrite: bool
        Overwrite existing output files instead of raising an error
    verbose: bool
        Print debug log messages
    """
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    config = KoffeeConfig(
        api_key=api_key,
        compute_type=compute_type,
        device=device,
        dry_run=dry_run,
        model=model,
        overwrite=overwrite,
        output_dir=output_dir,
        output_name=output_name,
        overlay=overlay,
        source_language=source_lang,
        subtitle_format=subtitle_format,
        target_language=target_lang,
        translation_backend=translation_backend,
    )

    resolved_paths = _resolve_paths(file_path)

    for video in resolved_paths:
        config = _check_embedded_subtitles(video, config)

    if config.dry_run:
        _print_dry_run(resolved_paths, config)
        return

    total = len(resolved_paths)
    with _create_progress_bar() as progress:
        for i, video in enumerate(resolved_paths, 1):
            if total > 1:
                log.info(f"[{i}/{total}] Processing {video.name}")
            _translate_with_progress(video, config, progress)


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
            mode = f"ASR ({config.model}) + translation ({config.translation_backend})"
        log.info(f"  {path.name} -> {mode}")

    log.info(f"[dry-run] Target language: {config.target_language}")
    log.info(f"[dry-run] Output format: {config.subtitle_format}")
    if config.overlay != "none":
        log.info(f"[dry-run] Subtitles will be embedded into video ({config.overlay})")


def _check_embedded_subtitles(video: Path, config: KoffeeConfig) -> KoffeeConfig:
    """Checks for embedded subtitles and prompts user to use them."""
    if video.suffix.lower() in SUBTITLE_EXTENSIONS:
        return config

    tracks = get_subtitle_tracks(video)
    if not tracks:
        return config

    track_count = len(tracks)
    log.info(f"Found {track_count} embedded subtitle track(s) in {video.name}.")

    response = input("Translate embedded subtitles instead of running ASR? [Y/n] ")
    if response.strip().lower() not in ("", "y", "yes"):
        return config

    track_index, source_language = _select_subtitle_track(tracks)
    updates = {"use_embedded_subtitles": True, "subtitle_track_index": track_index}
    if source_language:
        updates["source_language"] = source_language

    return config.model_copy(update=updates)


def _select_subtitle_track(tracks: list[dict]) -> tuple[int, str | None]:
    """Prompts user to select a subtitle track if multiple are available."""
    if len(tracks) == 1:
        language = tracks[0].get("tags", {}).get("language")
        return 0, language

    log.info("Available subtitle tracks:")
    for i, track in enumerate(tracks):
        tags = track.get("tags", {})
        lang = tags.get("language", "unknown")
        title = tags.get("title", "")
        label = f"  [{i}] {lang}"
        if title:
            label += f" — {title}"
        log.info(label)

    response = input(f"Select track [0-{len(tracks) - 1}] (default 0): ")
    index = int(response.strip()) if response.strip().isdigit() else 0
    index = max(0, min(index, len(tracks) - 1))

    language = tracks[index].get("tags", {}).get("language")
    return index, language


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
    video: Path,
    config: KoffeeConfig,
    progress: Progress,
) -> None:
    """Runs translation for a single file with ASR and translation progress bars."""
    skip_asr = (
        config.use_embedded_subtitles or video.suffix.lower() in SUBTITLE_EXTENSIONS
    )

    if skip_asr:
        translate_task = progress.add_task("Translating", total=100)
        translate(
            video_file_path=video,
            config=config,
            on_translate_progress=_make_progress_callback(progress, translate_task),
        )
    else:
        asr_task = progress.add_task("Transcribing", total=100)
        translate_task = progress.add_task("Translating", total=100, start=False)

        def on_asr_progress(ratio: float) -> None:
            progress.update(asr_task, completed=ratio * 100)
            if ratio >= 1.0:
                progress.stop_task(asr_task)
                progress.start_task(translate_task)

        translate(
            video_file_path=video,
            config=config,
            on_asr_progress=on_asr_progress,
            on_translate_progress=_make_progress_callback(progress, translate_task),
        )


@app.command()
def info() -> None:
    """Display system information for debugging."""
    log.info("[koffee info]")

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
        log.info(f"  CUDA: {'available' if cuda_available else 'not available'}")
        if cuda_available:
            log.info(f"  GPU: {device_name}")
    except ImportError:
        log.info("  torch: not installed")

    config = KoffeeConfig(**load_config_file())
    log.info(f"  default model: {config.model}")
    log.info(f"  default backend: {config.translation_backend}")
    log.info(f"  config file: {_find_config_path() or 'none'}")


def _find_config_path() -> Path | None:
    """Returns the path to the active config file, or None."""
    for path in CONFIG_SEARCH_PATHS:
        if path.is_file():
            return path
    return None


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
        lang = tags.get("language", "unknown")
        title = tags.get("title", "")
        label = f"  [{i}] {lang}"
        if title:
            label += f" — {title}"
        log.info(label)


def main() -> None:
    """Wraps app() so that it is accessible to poetry."""
    app()


if __name__ == "__main__":
    main()
