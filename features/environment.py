"""Behave environment."""

from pathlib import Path

from behave.runner import Context


def before_all(context: Context) -> None:
    """Sets up for behavior testing."""
    temp_dir = Path("scratch/tmp")
    temp_dir.mkdir(parents=True, exist_ok=True)
    context.temp_dir = temp_dir
