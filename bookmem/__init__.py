"""BookMem: machine-readable Markdown book corpus for agent retrieval."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("bookmem")
except PackageNotFoundError:  # running from a source tree that is not installed
    __version__ = "0.0.0+source"

__author__ = "Martyn Forryan"
