"""The koffee Configuration."""

from pathlib import Path

from pydantic import BaseModel


class KoffeeConfig(BaseModel):
    """Configuration data model for koffee."""

    api_key: str | None = None
    compute_type: str = "default"
    device: str = "auto"
    model: str = "large-v3"
    output_dir: Path | None = None
    output_name: str | None = None
    overlay_video: bool = False
    subtitle_format: str = "vtt"
    target_language: str = "en"
    translation_backend: str = "whisper"

    class DictConfig:
        """Configuration to remove all leading and trailing white space."""

        str_strip_whitespace = True
