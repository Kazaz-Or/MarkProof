"""MarkProof — markdown linting and validation CLI."""

try:
    from ._version import version as __version__
except ImportError:  # package not installed / _version.py not yet generated
    __version__ = "0.0.0"
