"""The koffee package."""

from importlib.metadata import version

from .translate import translate

all = [translate]

__version__ = version("koffee")
