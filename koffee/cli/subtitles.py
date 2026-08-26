"""Commands for subtitle conversion, embedding, and inspection."""

from pathlib import Path
from typing import Annotated

from cyclopts import Parameter, validators

from koffee.api import _check_output_collision, _write_embedded_video, _write_output
from koffee.cli.app import app, log, options_group
from koffee.embed import validate_embedding
from koffee.exceptions import IncompatibleOptionsError
from koffee.subtitle import (
    generate_subtitles,
    get_subtitle_tracks,
    parse_subtitle_file,
)


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
        subtitle_format=subtitle_format,
        output_dir=output_dir,
        output_name=output_name,
        overwrite=overwrite,
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

    _check_standalone_embed_output(output_path, video_path, subtitle_path)
    _check_output_collision(output_path, overwrite)
    validate_embedding(output_path, mode)
    result = _write_embedded_video(
        subtitle_path,
        video_path,
        output_path,
        embed_mode=mode,
        delete_subtitle=False,
    )
    log.info(f"Output saved to {result}")


@app.command()
def tracks(
    file_path: Annotated[Path, Parameter(validator=validators.Path(exists=True))],
) -> None:
    """List embedded subtitle tracks in a video file."""
    track_list = get_subtitle_tracks(file_path)

    if not track_list:
        log.info(f"No text subtitle tracks found in {file_path.name}.")
        return

    log.info(f"Subtitle tracks in {file_path.name}:")
    for track in track_list:
        language = track.language or "unknown"
        label = f"  [{track.subtitle_ordinal}] {language}"
        if track.title:
            label += f" — {track.title}"
        log.info(label)


def _check_standalone_embed_output(
    output_path: Path,
    video_path: Path,
    subtitle_path: Path,
) -> None:
    """Rejects an output path that identifies either standalone input."""
    for input_path in (video_path, subtitle_path):
        try:
            aliases_input = output_path.exists() and input_path.samefile(output_path)
        except OSError:
            aliases_input = False
        if aliases_input or input_path.resolve() == output_path.resolve():
            error_message = f"Output file must differ from input file: {input_path}."
            raise IncompatibleOptionsError(error_message)
