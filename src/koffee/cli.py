"""The koffee CLI."""

from pathlib import Path

import koffee
from koffee.translate import translate
from koffee.exceptions import InvalidVideoFileError

from cyclopts import App
from typing import Optional


app = App(name="koffee", version=koffee.__version__)


def main() -> None:
    """Wraps app() so that it is accessible to poetry.

    Poetry's `scripts` configuration expects the entry point to be
    a callable function directly accessible from the module specified,
    but since main is decorated, that is not possible.
    """
    app()


@app.default
def cli(
    *file_path: Path,
    batch_size: int = 16,
    compute_type: str = "float32",
    device: str = "cpu",
    model: str = "large-v3",
    output_dir: Optional[Path] = None,
    output_name: Optional[str] = None,
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
