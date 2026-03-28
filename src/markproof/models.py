"""Pydantic models for MarkProof parse results."""

from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel


class CodeBlockKind(StrEnum):
    """Whether a code block installs packages or demonstrates library usage."""

    INSTALL = "install"
    USAGE = "usage"


class CodeBlock(BaseModel):
    """A single fenced code block extracted from a Markdown document."""

    source: str
    language: str
    line_number: int  # 1-based line of the opening fence
    kind: CodeBlockKind
    metadata: dict[str, str]  # parsed from preceding <!-- markproof:... --> comments


class ParseResult(BaseModel):
    """All code blocks found in a single Markdown file."""

    path: Path
    blocks: list[CodeBlock]
