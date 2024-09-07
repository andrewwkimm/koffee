"""The koffee CLI."""

import click

from koffee.translate import translate
from koffee.exceptions import InvalidVideoFileError


@click.command()
@click.argument("video_file_path", nargs=-1, required=True)
@click.option(
    "--batch_size",
    "-b",
    default=16,
    help="The batch size used when transcribing the audio.",
)
@click.option(
    "--device", "-d", default="cpu", help="The device used to load the model."
)
@click.option(
    "--compute_type", "-c", default="float32", help="Compute type used for the model."
)
@click.option(
    "--model",
    "-m",
    default="large-v3",
    help="The Whisper model instance to use.",
)
@click.option(
    "--output_path",
    "-o",
    type=click.Path(),
    default=None,
    help="Path for the directory of the output file.",
)
def main(
    video_file_path: str,
    batch_size: int,
    compute_type: str,
    device: str,
    model: str,
    output_path: str,
) -> None:
    """Gets a built video file with overlayed subtitles."""
    RED = "\033[91m"
    GREEN = "\033[92m"
    RESET = "\033[0m"

    try:
        click.echo(GREEN + "Processing video(s)..." + RESET)

        for video in video_file_path:
            translate(video, batch_size, device, compute_type, model, output_path)

        click.echo(GREEN + "Processing successful!" + RESET)
    except InvalidVideoFileError as excinfo:
        click.echo(f"{RED}InvalidVideoFileError: {excinfo}{RESET}")


if __name__ == "__main__":
    main()
