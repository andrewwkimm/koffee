"""The koffee CLI."""

import logging
from pathlib import Path

from cyclopts import App, Group, Parameter, validators
from rich.logging import RichHandler
from typing import Annotated, Optional

from koffee.data.config import koffeeConfig
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


@app.default()
def cli(
    *file_path: Annotated[Path, Parameter(validator=validators.Path(exists=True))],
    compute_type: Annotated[str, Parameter(name=("--compute-type", "-c"))] = "default",
    device: Annotated[str, Parameter(name=("--device", "-d"))] = "auto",
    model: Annotated[str, Parameter(name=("--model", "-m"))] = "large-v3",
    output_dir: Optional[
        Annotated[Path, Parameter(name=("--output-dir", "-o"))]
    ] = None,
    output_name: Optional[
        Annotated[str, Parameter(name=("--output-name", "-n"))]
    ] = None,
    target_language: Annotated[str, Parameter(name=("--target_lang", "-t"))] = "en",
    srt: Annotated[bool, Parameter(name=("--srt", "-s"), group=options_group)] = False,
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
    srt: bool
        Write the translated SRT file to disk
    target_language: str
        Language to which the video should be translated.
    verbose: bool
        Print debug log messages.
    """
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    config = koffeeConfig(
        compute_type=compute_type,
        device=device,
        model=model,
        output_dir=output_dir,
        output_name=output_name,
        srt=srt,
        target_language=target_language,
    )

    for video in file_path:
        translate(video_file_path=video, config=config)


def main() -> None:
    """Wraps app() so that it is accessible to poetry.

    Poetry's `scripts` configuration expects the entry point to be a callable
    function directly accessible from the module specified, but since main is
    decorated, that is not possible.
    """
    app()


if __name__ == "__main__":
    app()
