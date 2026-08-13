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
LANGUAGE_NAMES = {
    "af": "Afrikaans",
    "am": "Amharic",
    "ar": "Arabic",
    "as": "Assamese",
    "az": "Azerbaijani",
    "ba": "Bashkir",
    "be": "Belarusian",
    "bg": "Bulgarian",
    "bn": "Bengali",
    "bo": "Tibetan",
    "br": "Breton",
    "bs": "Bosnian",
    "ca": "Catalan",
    "cs": "Czech",
    "cy": "Welsh",
    "da": "Danish",
    "de": "German",
    "el": "Greek",
    "en": "English",
    "es": "Spanish",
    "et": "Estonian",
    "eu": "Basque",
    "fa": "Persian",
    "fi": "Finnish",
    "fo": "Faroese",
    "fr": "French",
    "gl": "Galician",
    "gu": "Gujarati",
    "ha": "Hausa",
    "haw": "Hawaiian",
    "he": "Hebrew",
    "hi": "Hindi",
    "hr": "Croatian",
    "ht": "Haitian Creole",
    "hu": "Hungarian",
    "hy": "Armenian",
    "id": "Indonesian",
    "is": "Icelandic",
    "it": "Italian",
    "ja": "Japanese",
    "jw": "Javanese",
    "ka": "Georgian",
    "kk": "Kazakh",
    "km": "Khmer",
    "kn": "Kannada",
    "ko": "Korean",
    "la": "Latin",
    "lb": "Luxembourgish",
    "ln": "Lingala",
    "lo": "Lao",
    "lt": "Lithuanian",
    "lv": "Latvian",
    "mg": "Malagasy",
    "mi": "Maori",
    "mk": "Macedonian",
    "ml": "Malayalam",
    "mn": "Mongolian",
    "mr": "Marathi",
    "ms": "Malay",
    "mt": "Maltese",
    "my": "Myanmar",
    "ne": "Nepali",
    "nl": "Dutch",
    "nn": "Nynorsk",
    "no": "Norwegian",
    "oc": "Occitan",
    "pa": "Punjabi",
    "pl": "Polish",
    "ps": "Pashto",
    "pt": "Portuguese",
    "ro": "Romanian",
    "ru": "Russian",
    "sa": "Sanskrit",
    "sd": "Sindhi",
    "si": "Sinhala",
    "sk": "Slovak",
    "sl": "Slovenian",
    "sn": "Shona",
    "so": "Somali",
    "sq": "Albanian",
    "sr": "Serbian",
    "su": "Sundanese",
    "sv": "Swedish",
    "sw": "Swahili",
    "ta": "Tamil",
    "te": "Telugu",
    "tg": "Tajik",
    "th": "Thai",
    "tk": "Turkmen",
    "tl": "Tagalog",
    "tr": "Turkish",
    "tt": "Tatar",
    "uk": "Ukrainian",
    "ur": "Urdu",
    "uz": "Uzbek",
    "vi": "Vietnamese",
    "yi": "Yiddish",
    "yo": "Yoruba",
    "yue": "Cantonese",
    "zh": "Chinese",
}

CONFIG_FILENAME = "koffee.toml"
CONFIG_SEARCH_PATHS = [
    Path.cwd() / CONFIG_FILENAME,
    Path.home() / ".config" / "koffee" / CONFIG_FILENAME,
]


class KoffeeConfig(BaseModel):
    """Configuration data model for koffee."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    api_key: str | None = None
    compute_type: str = "default"
    device: str = "auto"
    whisper_model: str = "large-v3"
    output_dir: Path | None = None
    output_name: str | None = None
    embed: Literal["none", "soft", "hard"] = "none"
    source_language: str = "auto"
    subtitle_format: Literal["srt", "vtt", "ass"] = "vtt"
    target_language: str = "en"
    provider: Literal["whisper", "gemini", "chatgpt", "claude", "ollama"] = "whisper"
    llm_model: str | None = None
    chunk_size: int | None = None
    context_size: int | None = None
    sleep_requests: int | None = None
    prompt: str | None = None
    dry_run: bool = False
    overwrite: bool = False
    vad_filter: bool = True
    subtitle_track_index: int = 0
    use_embedded_subtitles: bool = False
    on_translation_failure: Literal["prompt", "save", "abort"] = "prompt"

    @model_validator(mode="before")
    @classmethod
    def _resolve_api_key(cls, values: dict) -> dict:
        """Falls back to environment variables based on the translation backend."""
        if values.get("api_key") is not None:
            return values

        env_vars = {
            "gemini": "GOOGLE_API_KEY",
            "chatgpt": "OPENAI_API_KEY",
            "claude": "ANTHROPIC_API_KEY",
        }
        backend = values.get("provider", "whisper")
        env_var = env_vars.get(backend)
        if env_var:
            values["api_key"] = os.environ.get(env_var)

        return values

    @field_validator("source_language")
    @classmethod
    def _validate_source_language(
        cls,
        value: str,
    ) -> str:
        """Validates source language and auto-detection."""
        return _validate_language_code(
            value,
            allow_auto=True,
        )

    @field_validator("target_language")
    @classmethod
    def _validate_target_language(
        cls,
        value: str,
    ) -> str:
        """Validates an explicit target language."""
        return _validate_language_code(
            value,
            allow_auto=False,
        )

    @field_validator("whisper_model")
    @classmethod
    def _validate_whisper_model(cls, value: str) -> str:
        """Validates that the model name is a known Whisper model."""
        if value not in WHISPER_MODELS:
            error_message = (
                f"Unknown Whisper model: {value!r}. "
                f"Available models: {', '.join(sorted(WHISPER_MODELS))}"
            )
            raise ValueError(error_message)
        return value

    @field_validator("chunk_size", "context_size")
    @classmethod
    def _validate_positive_size(cls, value: int | None) -> int | None:
        """Rejects non-positive chunk/context sizes that would stall translation."""
        if value is not None and value <= 0:
            error_message = f"Size must be a positive integer, got {value}."
            raise ValueError(error_message)
        return value

    @field_validator("sleep_requests")
    @classmethod
    def _validate_sleep_requests(cls, value: int | None) -> int | None:
        """Rejects negative sleep durations; zero is valid for no delay."""
        if value is not None and value < 0:
            error_message = f"sleep_requests must be non-negative, got {value}."
            raise ValueError(error_message)
        return value

    @field_validator("subtitle_track_index")
    @classmethod
    def _validate_subtitle_track_index(
        cls,
        value: int,
    ) -> int:
        """Rejects negative subtitle-track indexes."""
        if value < 0:
            error_message = f"subtitle_track_index must be non-negative, got {value}."
            raise ValueError(error_message)
        return value


def load_config_file(
    path: Path | None = None,
) -> dict:
    """Loads an explicit config or searches defaults.

    Raises:
        FileNotFoundError: An explicit path does not exist.
    """
    if path is not None:
        return _read_config_file(path)

    for config_path in CONFIG_SEARCH_PATHS:
        if config_path.is_file():
            return _read_config_file(config_path)

    return {}


def _read_config_file(path: Path) -> dict:
    """Loads one TOML configuration file."""
    log.debug(f"Loading config from {path}")
    with path.open("rb") as config_file:
        return tomllib.load(config_file)


def _validate_language_code(
    value: str,
    allow_auto: bool,
) -> str:
    """Validates a language code for its assigned role."""
    allowed_codes = LANGUAGE_CODES if allow_auto else LANGUAGE_CODES - {"auto"}
    if value not in allowed_codes:
        error_message = (
            f"Unsupported language code: {value!r}. "
            f"Use one of: "
            f"{', '.join(sorted(allowed_codes))}"
        )
        raise ValueError(error_message)
    return value
