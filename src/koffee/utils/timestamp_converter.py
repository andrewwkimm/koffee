"""Float to timestamp converter."""

from datetime import timedelta
import logging
from typing import Union

from koffee.exceptions import InvalidSubtitleFormatError


log = logging.getLogger(__name__)


def convert_to_timestamp(seconds: Union[float, int], subtitle_format: str) -> str:
    """Converts seconds to SRT timestamp format."""
    log.debug("subtitle_format: " + repr(subtitle_format))

    ms = int((seconds % 1) * 1000)
    ts = timedelta(seconds=int(seconds))
    hours, remainder = divmod(ts.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    if subtitle_format == "srt":
        timestamp = f"{hours:02}:{minutes:02}:{seconds:02},{ms:03}"
    elif subtitle_format == "vtt":
        timestamp = f"{hours:02}:{minutes:02}:{seconds:02}.{ms:03}"
    else:
        error_message = f"Invalid or unsupported subtitle format: {subtitle_format}"
        raise InvalidSubtitleFormatError(error_message)

    return timestamp
