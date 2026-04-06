"""The koffee Configuration."""

import logging
import tomllib
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

log = logging.getLogger(__name__)

CONFIG_FILENAME = "koffee.toml"
CONFIG_SEARCH_PATHS = [
    Path.cwd() / CONFIG_FILENAME,
    Path.home() / ".config" / "koffee" / CONFIG_FILENAME,
]


class KoffeeConfig(BaseModel):
    """Configuration data model for koffee."""

    model_config = ConfigDict(str_strip_whitespace=True)

    api_key: str | None = None
    compute_type: str = "default"
    device: str = "auto"
    model: str = "large-v3"
    output_dir: Path | None = None
    output_name: str | None = None
    overlay_video: bool = False
    source_language: str = "ja"
    subtitle_format: Literal["srt", "vtt", "ass"] = "vtt"
    target_language: str = "en"
    translation_backend: Literal["whisper", "gemini"] = "whisper"
    translation_model: str = "gemini-2.5-flash"
    dry_run: bool = False
    overwrite: bool = False
    use_embedded_subtitles: bool = False


def load_config_file(path: Path | None = None) -> dict:
    """Loads config from a TOML file, searching default paths if none given.

    Returns an empty dict if no config file is found.
    """
    search_paths = [path] if path is not None else CONFIG_SEARCH_PATHS

    for config_path in search_paths:
        if config_path.is_file():
            log.debug(f"Loading config from {config_path}")
            with config_path.open("rb") as f:
                return tomllib.load(f)

    return {}
