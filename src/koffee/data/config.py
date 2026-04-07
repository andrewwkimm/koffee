"""The koffee Configuration."""

import logging
import os
import tomllib
from pathlib import Path
from typing import Literal

from faster_whisper import available_models
from faster_whisper.tokenizer import _LANGUAGE_CODES
from pydantic import BaseModel, ConfigDict, field_validator, model_validator

log = logging.getLogger(__name__)

WHISPER_MODELS = set(available_models())
LANGUAGE_CODES = set(_LANGUAGE_CODES) | {"auto"}

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
    overlay: Literal["none", "soft", "hard"] = "none"
    source_language: str = "auto"
    subtitle_format: Literal["srt", "vtt", "ass"] = "vtt"
    target_language: str = "en"
    translation_backend: Literal["whisper", "gemini"] = "whisper"
    translation_model: str = "gemini-2.5-flash"
    dry_run: bool = False
    overwrite: bool = False
    subtitle_track_index: int = 0
    use_embedded_subtitles: bool = False

    @model_validator(mode="before")
    @classmethod
    def _resolve_api_key(cls, values: dict) -> dict:
        """Falls back to the GOOGLE_API_KEY environment variable."""
        if values.get("api_key") is None:
            values["api_key"] = os.environ.get("GOOGLE_API_KEY")
        return values

    @field_validator("source_language", "target_language")
    @classmethod
    def _validate_language(cls, value: str) -> str:
        """Validates that the language code is supported by Whisper."""
        if value not in LANGUAGE_CODES:
            error_message = (
                f"Unsupported language code: {value!r}. "
                f"Use one of: {', '.join(sorted(LANGUAGE_CODES - {'auto'}))}"
            )
            raise ValueError(error_message)
        return value

    @field_validator("model")
    @classmethod
    def _validate_model(cls, value: str) -> str:
        """Validates that the model name is a known Whisper model."""
        if value not in WHISPER_MODELS:
            error_message = (
                f"Unknown Whisper model: {value!r}. "
                f"Available models: {', '.join(sorted(WHISPER_MODELS))}"
            )
            raise ValueError(error_message)
        return value


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
