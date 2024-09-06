"""The koffee package."""

from importlib.metadata import version

from .translate import translate


__all__ = ["translate"]

__version__ = version("koffee")
