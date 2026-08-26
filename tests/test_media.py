"""Tests for immutable media and output capabilities."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from koffee.media import (
    MEDIA_CAPABILITIES,
    OutputPolicy,
    classify_media,
    resolve_output_path,
    soft_subtitle_codec,
)


@pytest.mark.parametrize(
    ("extension", "kind"),
    [(".opus", "audio"), (".m2ts", "video"), (".m4v", "video")],
)
def test_popular_ffmpeg_inputs_are_classified(extension: str, kind: str) -> None:
    """Tests classification of newly accepted standard FFmpeg inputs."""
    capability = classify_media(f"input{extension}")

    assert capability is not None
    assert capability.kind == kind


def test_media_capabilities_are_immutable() -> None:
    """Tests that capability declarations cannot be changed at runtime."""
    with pytest.raises(ValidationError):
        attribute_name = "kind"
        setattr(MEDIA_CAPABILITIES[0], attribute_name, "video")


def test_soft_codec_is_advertised_only_for_supported_outputs() -> None:
    """Tests that accepted input containers are not automatically output targets."""
    assert soft_subtitle_codec("output.mp4") == "mov_text"
    assert soft_subtitle_codec("output.avi") is None


def test_explicit_output_name_is_preserved_exactly() -> None:
    """Tests that explicit names receive no language, mode, or extension changes."""
    result = resolve_output_path(
        OutputPolicy(
            input_path=Path("input.mp4"),
            output_dir=Path("out"),
            output_name="custom.final",
            target_language="en",
            subtitle_format="vtt",
            embed_mode="soft",
        )
    )

    assert result == Path("out/custom.final")
