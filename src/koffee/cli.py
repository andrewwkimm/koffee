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
    video_file_path: str,
    batch_size: Optional[int] = 16,
    compute_type: Optional[str] = "float32",
    device: Optional[str] = "cpu",
    model: Optional[str] = "large-v3",
    output_path: Optional[Path] = None,
) -> None:
    """Automatic video translation and subtitling tool.

    Parameters
    ----------
    video_file_path: Path
        The path to the video file.
    batch_size: str
        The batch size used when transcribing the audio.
    compute_type: str
        Compute type used for the model.
    device: str
        The device used to load the model.
    model: str
        The Whisper model instance to use.
    output_path: Path
        The directory path for the translated video file.
    """
    try:
        translate(video_file_path, batch_size, compute_type, device, model, output_path)
    except InvalidVideoFileError:
        print("Inputted path is not a valid video file.")


if __name__ == "__main__":
    app()
