"""MarkProof configuration loader.

Reads ``markproof.toml`` from the project root.  Every field has a sensible
default so the file is entirely optional.

Example ``markproof.toml``::

    [readme]
    path = "README.md"

    [sections]
    managed = ["installation", "architecture", "tech_stack"]
"""

from __future__ import annotations

import tomllib
from pathlib import Path

from pydantic import BaseModel

# Section IDs understood by the generator.
SECTION_INSTALLATION = "installation"
SECTION_ARCHITECTURE = "architecture"
SECTION_TECH_STACK = "tech_stack"

ALL_SECTIONS: list[str] = [
    SECTION_INSTALLATION,
    SECTION_ARCHITECTURE,
    SECTION_TECH_STACK,
]


class ReadmeConfig(BaseModel):
    """Controls where the README is written."""

    path: str = "README.md"


class SectionsConfig(BaseModel):
    """Which sections MarkProof owns and will regenerate on every run."""

    managed: list[str] = list(ALL_SECTIONS)


class MarkProofConfig(BaseModel):
    """Top-level config model — mirrors the structure of ``markproof.toml``."""

    readme: ReadmeConfig = ReadmeConfig()
    sections: SectionsConfig = SectionsConfig()


def load_config(root: Path) -> MarkProofConfig:
    """Load ``markproof.toml`` from *root*, returning defaults if absent."""
    config_path = root / "markproof.toml"
    if not config_path.exists():
        return MarkProofConfig()
    with config_path.open("rb") as fh:
        data = tomllib.load(fh)
    return MarkProofConfig.model_validate(data)
