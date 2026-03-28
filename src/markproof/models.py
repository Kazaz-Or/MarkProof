"""Pydantic models and result dataclasses for MarkProof."""

from __future__ import annotations

from dataclasses import dataclass, field
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


@dataclass
class BlockResult:
    """Outcome of executing a single code block."""

    block: CodeBlock
    stdout: str = ""
    stderr: str = ""
    error: str | None = None  # "<ExcType>: <message>" if an exception was raised
    skipped: bool = False

    @property
    def passed(self) -> bool:
        return not self.skipped and self.error is None


@dataclass
class ExecutionResult:
    """Aggregated results from executing all blocks in a ParseResult."""

    path: Path
    results: list[BlockResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(r.passed or r.skipped for r in self.results)

    @property
    def errors(self) -> list[BlockResult]:
        return [r for r in self.results if r.error is not None]
