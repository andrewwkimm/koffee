"""Utility for calculating the MD5 checksum of a file."""

from pathlib import Path
from typing import Union

import hashlib


def get_md5_checksum(file_path: Union[Path, str]) -> str:
    """Calculates the MD5 checksum of a file."""
    md5_hash = hashlib.md5()

    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            md5_hash.update(chunk)

    md5_checksum = md5_hash.hexdigest()
    return md5_checksum