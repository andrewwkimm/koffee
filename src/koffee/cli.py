"""The koffee CLI."""

import logging
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

from koffee.data.config import KoffeeConfig
from koffee.translate import translate

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

options = KoffeeConfig()


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
    target_lang: Annotated[
        str, Parameter(name=("--target_lang", "-t"))
    ] = options.target_language,
    subtitle_format: Annotated[
        str, Parameter(name=("--subtitle_format", "-sf"))
    ] = options.subtitle_format,
    overlay_video: Annotated[
        bool, Parameter(name=("--overlay-video",), group=options_group)
    ] = options.overlay_video,
    translation_backend: Annotated[
        str, Parameter(name=("--translation_backend", "-tb"))
    ] = options.translation_backend,
    api_key: Annotated[str, Parameter(name=("--api_key", "-ak"), group=options_group)]
    | None = None,
    verbose: Annotated[
        bool, Parameter(name=("--verbose", "-V"), group=options_group)
    ] = False,
) -> None:
    """Automatic video translation and subtitling tool.

    Parameters
    ----------
    file_path: Path
        Path to the video or audio file
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
    overlay_video: bool
        Embed subtitles into the video as a soft subtitle track instead of
        outputting a subtitle file. Only valid for video file inputs.
    target_language: str
        Language to which the file should be translated
    translation_backend: str
        The backend service to use for the translation
    api_key: str
        API key for an LLM service
    verbose: bool
        Print debug log messages
    """
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    config = KoffeeConfig(
        api_key=api_key,
        compute_type=compute_type,
        device=device,
        model=model,
        output_dir=output_dir,
        output_name=output_name,
        overlay_video=overlay_video,
        subtitle_format=subtitle_format,
        target_language=target_lang,
        translation_backend=translation_backend,
    )

    resolved_paths = _resolve_paths(file_path)

    with _create_progress_bar() as progress:
        for video in resolved_paths:
            _translate_with_progress(video, config, progress)


def _resolve_paths(file_path: tuple) -> list[Path]:
    """Resolves glob patterns and returns a flat list of matched paths."""
    resolved_paths = []
    for pattern in file_path:
        matches = sorted(Path.cwd().glob(str(pattern)))
        if matches:
            resolved_paths.extend(matches)
        else:
            resolved_paths.append(Path(pattern))

    return resolved_paths


def _translate_with_progress(
    video: Path,
    config: KoffeeConfig,
    progress: Progress,
) -> None:
    """Runs translation for a single file with ASR and translation progress bars."""
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


def main() -> None:
    """Wraps app() so that it is accessible to poetry."""
    app()


if __name__ == "__main__":
    main()
