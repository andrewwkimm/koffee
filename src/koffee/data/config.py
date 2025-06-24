"""The koffee Configuration."""

from pathlib import Path

from pydantic import BaseModel


class KoffeeConfig(BaseModel):
    """Configuration data model for koffee."""

    compute_type: str = "default"
    device: str = "auto"
    model: str = "large-v3"
    output_dir: Path | None = None
    output_name: str | None = None
    subtitle_format: str = "srt"
    subtitles: bool = False
    target_language: str = "en"

    class DictConfig:
        """Configuration to remove all leading and trailing white space."""

        str_strip_whitespace = True
