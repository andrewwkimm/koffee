"""Cyclopts App and shared CLI setup."""

import logging
import tomllib

from cyclopts import App, Group, Parameter
from pydantic import ValidationError
from rich.logging import RichHandler

from koffee.schemas.config import KoffeeConfig, load_config_file

logging.basicConfig(
    level=logging.INFO, format="%(message)s", datefmt="[%X]", handlers=[RichHandler()]
)

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


def _load_cli_defaults() -> KoffeeConfig:
    """Loads CLI defaults from the config file, falling back on invalid input."""
    try:
        return KoffeeConfig(**load_config_file())
    except (ValidationError, tomllib.TOMLDecodeError) as exc:
        log.warning(f"Ignoring invalid config file for CLI defaults: {exc}")
        return KoffeeConfig()


defaults = _load_cli_defaults()
