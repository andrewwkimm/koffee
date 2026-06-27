"""Tests for koffee."""

import re

import koffee


def test_version_is_valid_semver() -> None:
    """Tests that the package version resolves to a well-formed semver string."""
    assert re.fullmatch(r"\d+\.\d+\.\d+", koffee.__version__)
