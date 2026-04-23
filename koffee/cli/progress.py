"""Progress bar helpers for CLI commands."""

from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)


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
