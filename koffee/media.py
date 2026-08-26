"""Immutable media capabilities and deterministic output policy."""

from pathlib import Path
from types import MappingProxyType
from typing import Literal

from pydantic import BaseModel, ConfigDict

MediaKind = Literal["audio", "video"]


class MediaCapability(BaseModel):
    """One accepted media extension and its optional soft-subtitle codec."""

    model_config = ConfigDict(frozen=True)

    extension: str
    kind: MediaKind
    soft_subtitle_codec: str | None = None


MEDIA_CAPABILITIES = (
    MediaCapability(extension=".aac", kind="audio"),
    MediaCapability(extension=".aiff", kind="audio"),
    MediaCapability(extension=".flac", kind="audio"),
    MediaCapability(extension=".m4a", kind="audio"),
    MediaCapability(extension=".mp3", kind="audio"),
    MediaCapability(extension=".ogg", kind="audio"),
    MediaCapability(extension=".opus", kind="audio"),
    MediaCapability(extension=".wav", kind="audio"),
    MediaCapability(extension=".wma", kind="audio"),
    MediaCapability(extension=".3gp", kind="video"),
    MediaCapability(extension=".avi", kind="video"),
    MediaCapability(extension=".flv", kind="video"),
    MediaCapability(extension=".m2ts", kind="video"),
    MediaCapability(extension=".m4v", kind="video", soft_subtitle_codec="mov_text"),
    MediaCapability(extension=".mkv", kind="video", soft_subtitle_codec="srt"),
    MediaCapability(extension=".mov", kind="video", soft_subtitle_codec="mov_text"),
    MediaCapability(extension=".mp4", kind="video", soft_subtitle_codec="mov_text"),
    MediaCapability(extension=".mpeg", kind="video"),
    MediaCapability(extension=".mpg", kind="video"),
    MediaCapability(extension=".ogv", kind="video"),
    MediaCapability(extension=".ts", kind="video"),
    MediaCapability(extension=".webm", kind="video", soft_subtitle_codec="webvtt"),
    MediaCapability(extension=".wmv", kind="video"),
)
MEDIA_CAPABILITY_BY_EXTENSION = MappingProxyType(
    {capability.extension: capability for capability in MEDIA_CAPABILITIES}
)
AUDIO_EXTENSIONS = frozenset(
    capability.extension
    for capability in MEDIA_CAPABILITIES
    if capability.kind == "audio"
)
VIDEO_EXTENSIONS = frozenset(
    capability.extension
    for capability in MEDIA_CAPABILITIES
    if capability.kind == "video"
)
SUPPORTED_EXTENSIONS = frozenset(MEDIA_CAPABILITY_BY_EXTENSION)


class OutputPolicy(BaseModel):
    """Inputs that determine one translated output path."""

    model_config = ConfigDict(frozen=True)

    input_path: Path
    output_dir: Path | None
    output_name: str | None
    target_language: str
    subtitle_format: str
    embed_mode: Literal["none", "soft", "hard"]


def classify_media(path: Path | str) -> MediaCapability | None:
    """Returns the capability for a recognized media extension."""
    return MEDIA_CAPABILITY_BY_EXTENSION.get(Path(path).suffix.lower())


def resolve_output_path(policy: OutputPolicy) -> Path:
    """Returns the deterministic publication path for translated output."""
    input_path = policy.input_path
    output_directory = policy.output_dir or input_path.parent
    if policy.output_name is not None:
        return output_directory / policy.output_name

    if policy.embed_mode != "none":
        name = (
            f"{input_path.stem}.{policy.target_language}."
            f"{policy.embed_mode}{input_path.suffix}"
        )
        return output_directory / name

    return output_directory / (
        f"{input_path.stem}.{policy.target_language}.{policy.subtitle_format}"
    )


def soft_subtitle_codec(output_path: Path | str) -> str | None:
    """Returns the advertised soft-subtitle codec for an output container."""
    capability = classify_media(output_path)
    return capability.soft_subtitle_codec if capability is not None else None
