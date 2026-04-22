"""The koffee package."""

from importlib.metadata import version

from .api import run

__all__ = ["run"]

__version__ = version("koffee")
