"""Supported-language display command."""

from rich.console import Console
from rich.table import Table

from koffee.cli.app import app
from koffee.schemas.config import (
    LANGUAGE_CODES,
    LANGUAGE_NAMES,
)


@app.command()
def languages() -> None:
    """List all supported language codes."""
    num_columns = 4
    codes = sorted(LANGUAGE_CODES - {"auto"})
    entries = [f"{code} ({LANGUAGE_NAMES.get(code, code)})" for code in codes]

    table = Table(show_header=False, box=None, pad_edge=False, expand=True)
    for _ in range(num_columns):
        table.add_column()

    for i in range(0, len(entries), num_columns):
        row = entries[i : i + num_columns]
        row += [""] * (num_columns - len(row))
        table.add_row(*row)

    console = Console()
    console.print(table)
    console.print(f"\n[bold]{len(codes)}[/bold] supported languages")
