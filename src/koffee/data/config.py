"""The koffee Configuration."""

from pathlib import Path
from typing import Optional

from pydantic import BaseModel


class koffeeConfig(BaseModel):
    """Configuration data model for koffee."""

    batch_size: int = 16
    compute_type: str = "float32"
    device: str = "cpu"
    model: str = "large-v3"
    output_dir: Optional[Path] = None
    output_name: Optional[str] = None
    srt: Optional[bool] = False
    target_language: str = "en"

    class Config:
        """Configuration to remove all leading and trailing white space."""

        str_strip_whitespace = True
