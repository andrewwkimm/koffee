"""The koffee Configuration."""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict


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
    subtitle_format: Literal["srt", "vtt"] = "vtt"
    target_language: str = "en"
    translation_backend: Literal["whisper", "gemini"] = "whisper"
    translation_model: str = "gemini-2.5-flash"
