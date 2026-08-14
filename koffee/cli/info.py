"""Runtime and installation information command."""

import shutil
import subprocess
import sys
from pathlib import Path

from koffee.cli.app import app, log
from koffee.schemas.config import (
    CONFIG_SEARCH_PATHS,
    KoffeeConfig,
    load_config_file,
)


@app.command()
def info() -> None:
    """Display system information for debugging."""
    log.info("[koffee info]")

    import koffee  # noqa: PLC0415

    log.info(f"  koffee: {koffee.__version__}")
    log.info(f"  python: {sys.version.split()[0]}")

    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
        version_line = result.stdout.split("\n")[0]
        log.info(f"  ffmpeg: {version_line}")
    else:
        log.info("  ffmpeg: not found")

    ffprobe_path = shutil.which("ffprobe")
    log.info(f"  ffprobe: {'found' if ffprobe_path else 'not found'}")

    try:
        import torch  # noqa: PLC0415

        cuda_available = torch.cuda.is_available()
        device_name = torch.cuda.get_device_name(0) if cuda_available else "N/A"
        log.info(f"  torch: {torch.__version__}")
        log.info(f"  CUDA: {'available' if cuda_available else 'not available'}")
        if cuda_available:
            log.info(f"  GPU: {device_name}")
            vram_bytes = torch.cuda.get_device_properties(0).total_memory
            log.info(f"  VRAM: {vram_bytes / 1024**3:.1f} GB")
    except ImportError:
        log.info("  torch: not installed")

    try:
        import faster_whisper  # noqa: PLC0415

        log.info(f"  faster-whisper: {faster_whisper.__version__}")
    except ImportError:
        log.info("  faster-whisper: not installed")

    config = KoffeeConfig(**load_config_file())
    log.info(f"  default whisper model: {config.transcription_model}")
    log.info(f"  default backend: {config.translator}")
    log.info(f"  config file: {_find_config_path() or 'none'}")


def _find_config_path() -> Path | None:
    """Returns the path to the active config file, or None."""
    for path in CONFIG_SEARCH_PATHS:
        if path.is_file():
            return path
    return None
