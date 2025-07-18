"""The koffee CLI."""

import logging
from pathlib import Path
from typing import Annotated

from cyclopts import App, Group, Parameter, validators
from rich.logging import RichHandler

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


@app.default()
def cli(  # noqa: PLR0913
    *file_path: Annotated[Path, Parameter(validator=validators.Path(exists=True))],
    compute_type: Annotated[
        str, Parameter(name=("--compute-type", "-c"))
    ] = options.compute_type,
    device: Annotated[str, Parameter(name=("--device", "-d"))] = options.device,
    model: Annotated[str, Parameter(name=("--model", "-m"))] = options.model,
    output_dir: Annotated[Path, Parameter(name=("--output_dir", "-o"))] | None = None,
    output_name: Annotated[str, Parameter(name=("--output_name", "-n"))] | None = None,
    target_language: Annotated[
        str, Parameter(name=("--target_lang", "-t"))
    ] = options.target_language,
    subtitle_format: Annotated[
        str, Parameter(name=("--subtitle_format", "-sf"))
    ] = options.subtitle_format,
    subtitles: Annotated[
        bool, Parameter(name=("--subtitles", "-s"), group=options_group)
    ] = options.subtitles,
    verbose: Annotated[
        bool, Parameter(name=("--verbose", "-V"), group=options_group)
    ] = False,
) -> None:
    """Automatic video translation and subtitling tool.

    Parameters
    ----------
    file_path: Path
        Path to the video file.
    compute_type: str
        Type to use for computation.
    device: str
        Device to use for computation.
    model: str
        The Whisper model instance to use.
    output_dir: Path
        Directory for the output file.
    output_name: str
        Name of the output file.
    subtitle_format: str
        Format to use for the subtitles.
    subtitles: bool
        Write the translated subtitle file to disk
    target_language: str
        Language to which the video should be translated.
    verbose: bool
        Print debug log messages.
    """
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    config = KoffeeConfig(
        compute_type=compute_type,
        device=device,
        model=model,
        output_dir=output_dir,
        output_name=output_name,
        subtitle_format=subtitle_format,
        subtitles=subtitles,
        target_language=target_language,
    )
    for video in file_path:
        translate(video_file_path=video, config=config)


def main() -> None:
    """Wraps app() so that it is accessible to poetry."""
    app()


if __name__ == "__main__":
    main()
