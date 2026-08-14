"""CLI configuration resolution."""

from collections.abc import Mapping
from pathlib import Path

from koffee.schemas.config import (
    KoffeeConfig,
    load_config_file,
)


def _resolve_config(
    config_path: Path | None,
    cli_values: Mapping[str, object | None],
) -> KoffeeConfig:
    """Resolves defaults, TOML, and explicit CLI values."""
    default_values = KoffeeConfig().model_dump()
    file_values = load_config_file(config_path)
    overrides = {name: value for name, value in cli_values.items() if value is not None}
    return KoffeeConfig(**(default_values | file_values | overrides))
