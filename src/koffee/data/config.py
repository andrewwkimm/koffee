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

    model_config = ConfigDict(str_strip_whitespace=True)

    api_key: str | None = None
    compute_type: str = "default"
    device: str = "auto"
    whisper_model: str = "large-v3"
    output_dir: Path | None = None
    output_name: str | None = None
    overlay: Literal["none", "soft", "hard"] = "none"
    source_language: str = "auto"
    subtitle_format: Literal["srt", "vtt", "ass"] = "vtt"
    target_language: str = "en"
    translator: Literal["whisper", "gemini", "chatgpt", "claude"] = "whisper"
    llm_model: str | None = None
    prompt: str | None = None
    dry_run: bool = False
    overwrite: bool = False
    subtitle_track_index: int = 0
    use_embedded_subtitles: bool = False

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
        backend = values.get("translator", "whisper")
        env_var = env_vars.get(backend)
        if env_var:
            values["api_key"] = os.environ.get(env_var)

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
