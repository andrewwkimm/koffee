"""Cyclopts application and shared CLI setup."""

import logging

from cyclopts import App, Group, Parameter
from rich.logging import RichHandler

log = logging.getLogger(__name__)

app = App(
    default_parameter=Parameter(negative=""),
    group_arguments=Group("Arguments", sort_key=0),
    group_commands=Group("Commands", sort_key=1),
    group_parameters=Group("Parameters", sort_key=2),
    name="koffee",
    version_flags=["--version", "-V"],
)

options_group = Group("Options", sort_key=3)

app["--help"].group = options_group
app["--version"].group = options_group


def _configure_logging() -> None:
    """Configures logging at the executable boundary."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler()],
    )
