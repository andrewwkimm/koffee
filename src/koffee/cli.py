"""The koffee CLI."""

from pathlib import Path

import koffee
from koffee.translate import translate
from koffee.exceptions import InvalidVideoFileError

from cyclopts import App, Parameter, validators
from typing import Annotated, Optional


app = App(name="koffee", version=koffee.__version__, version_flags=["--version", "-v"])


def main() -> None:
    """Wraps app() so that it is accessible to poetry.

    Poetry's `scripts` configuration expects the entry point to be a callable
    function directly accessible from the module specified, but since main is
    decorated, that is not possible.
    """
    app()


@app.default
def cli(
    *file_path: Annotated[Path, Parameter(validator=validators.Path(exists=True))],
    batch_size: Annotated[int, Parameter(name=("--batch-size", "-b"))] = 16,
    compute_type: Annotated[str, Parameter(name=("--compute-type", "-c"))] = "float32",
    device: Annotated[str, Parameter(name=("--device", "-d"))] = "cpu",
    model: Annotated[str, Parameter(name=("--model", "-m"))] = "large-v3",
    output_dir: Optional[
        Annotated[Path, Parameter(name=("--output-dir", "-o"))]
    ] = None,
    output_name: Optional[
        Annotated[str, Parameter(name=("--output-dir", "-O"))]
    ] = None,
) -> None:
    """Automatic video translation and subtitling tool.

    Parameters
    ----------
    file_path: Path
        Path to the video file.
    batch_size: str
        Batch size used when transcribing the audio.
    compute_type: str
        Device used to load the model.
    device: str
        Compute type used for the model.
    model: str
        The Whisper model instance to use.
    output_dir: Path
        Directory for the output file.
    output_name: str
        Name of the output file.
    """
    try:
        for video in file_path:
            translate(
                video,
                batch_size,
                compute_type,
                device,
                model,
                output_dir,
                output_name,
            )
    except InvalidVideoFileError:
        print("Inputted path is not a valid video file.")


if __name__ == "__main__":
    app()
