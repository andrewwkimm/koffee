"""Float to timestamp converter."""

from datetime import timedelta
from typing import Union


def convert_to_timestamp(seconds: Union[float, int], subtitle_format: str) -> str:
    """Converts seconds to SRT timestamp format."""
    ms = int((seconds % 1) * 1000)
    ts = timedelta(seconds=int(seconds))
    hours, remainder = divmod(ts.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    if subtitle_format == "srt":
        timestamp = f"{hours:02}:{minutes:02}:{seconds:02},{ms:03}"
    elif subtitle_format == "vtt":
        timestamp = f"{hours:02}:{minutes:02}:{seconds:02}.{ms:03}"
    else:
        raise ValueError("Unsupported format. Choose 'srt' or 'vtt'.")

    return timestamp
