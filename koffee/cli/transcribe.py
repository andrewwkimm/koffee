"""Standalone transcription command."""

from pathlib import Path
from typing import Annotated

from cyclopts import Parameter, validators

from koffee import asr
from koffee.api import _write_output
from koffee.cli.app import app, log, options_group
from koffee.cli.configuration import _resolve_config
from koffee.cli.progress import (
    _create_progress_bar,
    _make_progress_callback,
)
from koffee.subtitle import generate_subtitles


@app.command()
def transcribe(
    file_path: Annotated[
        Path,
        Parameter(validator=validators.Path(exists=True)),
    ],
    compute_type: Annotated[
        str | None,
        Parameter(name=("--compute-type", "-c")),
    ] = None,
    device: Annotated[
        str | None,
        Parameter(name=("--device", "-d")),
    ] = None,
    transcription_model: Annotated[
        str | None,
        Parameter(name=("--transcription-model", "-m")),
    ] = None,
    output_dir: Annotated[
        Path,
        Parameter(name=("--output-dir", "-o")),
    ]
    | None = None,
    output_name: Annotated[
        str,
        Parameter(name=("--output-name", "-n")),
    ]
    | None = None,
    subtitle_format: Annotated[
        str | None,
        Parameter(name=("--subtitle-format", "-f")),
    ] = None,
    vad_filter: Annotated[
        bool | None,
        Parameter(
            negative="--no-vad-filter",
            group=options_group,
        ),
    ] = None,
    overwrite: Annotated[
        bool | None,
        Parameter(
            name=("--overwrite",),
            group=options_group,
        ),
    ] = None,
) -> None:
    """Transcribes audio to subtitles without translation."""
    config = _resolve_config(
        None,
        {
            "compute_type": compute_type,
            "device": device,
            "transcription_model": transcription_model,
            "output_dir": output_dir,
            "output_name": output_name,
            "subtitle_format": subtitle_format,
            "vad_filter": vad_filter,
            "overwrite": overwrite,
        },
    )

    with _create_progress_bar() as progress:
        asr_task = progress.add_task(
            "Transcribing",
            total=100,
        )
        transcript = asr.transcribe(
            str(file_path),
            config.compute_type,
            config.device,
            config.transcription_model,
            "transcribe",
            on_progress=_make_progress_callback(
                progress,
                asr_task,
            ),
            vad_filter=config.vad_filter,
        )

    output_directory = config.output_dir or file_path.parent
    subtitle_path = generate_subtitles(
        config.subtitle_format,
        transcript.segments,
        output_directory,
    )
    target_path = _write_output(
        subtitle_path,
        file_path,
        config.subtitle_format,
        config.output_dir,
        config.output_name,
        config.overwrite,
    )
    log.info(f"Output saved to {target_path}")
