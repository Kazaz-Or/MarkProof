"""Core Markdown parser for MarkProof.

Responsibilities
----------------
1. Extract every fenced code block from a Markdown document, recording its
   language tag, source content, and 1-based opening line number.
2. Associate ``<!-- markproof:key=value flag -->`` HTML comments that appear
   immediately before a block (blank lines permitted between them) with that
   block as structured metadata.
3. Classify each block as INSTALL or USAGE by detecting package-manager
   invocations (pip, uv, conda, poetry, pipenv) inside the block source.
"""

from __future__ import annotations

import re
from pathlib import Path

from .models import CodeBlock, CodeBlockKind, ParseResult

_COMMENT_RE = re.compile(r"<!--\s*markproof:([^>]+?)-->", re.IGNORECASE)

_FENCE_OPEN_RE = re.compile(r"^(?P<fence>`{3,}|~{3,})(?P<lang>\w*)\s*$")

_INSTALL_RE = re.compile(
    r"^\s*(?:"
    r"pip3?\s+install"
    r"|uv\s+(?:add|pip\s+install)"
    r"|conda\s+install"
    r"|poetry\s+add"
    r"|pipenv\s+install"
    r")\b",
    re.MULTILINE,
)


def _parse_comment_metadata(raw: str) -> dict[str, str]:
    """Parse ``key=value`` and bare ``flag`` tokens from a markproof comment.

    Examples
    --------
    ``"skip version=3.10 id=ex-1"``
    → ``{"skip": "true", "version": "3.10", "id": "ex-1"}``
    """
    result: dict[str, str] = {}
    for token in raw.split():
        key, sep, value = token.partition("=")
        result[key.strip()] = value.strip() if sep else "true"
    return result


def _classify(source: str) -> CodeBlockKind:
    """Return INSTALL if the source contains a package-manager command."""
    return CodeBlockKind.INSTALL if _INSTALL_RE.search(source) else CodeBlockKind.USAGE


def _closing_fence_re(fence: str) -> re.Pattern[str]:
    """Build a regex that matches a closing fence for *fence*.

    The closing fence must use the same character and be at least as long.
    """
    char = re.escape(fence[0])
    return re.compile(rf"^{char}{{{len(fence)},}}\s*$")


def parse_text(text: str, path: Path) -> ParseResult:
    """Parse *text* as Markdown and return all fenced code blocks found.

    Parameters
    ----------
    text:
        Raw Markdown content.
    path:
        The logical path of the document (stored on the result; not read here).
    """
    lines = text.splitlines()
    blocks: list[CodeBlock] = []
    pending_meta: dict[str, str] = {}

    i = 0
    while i < len(lines):
        line = lines[i]

        comment_match = _COMMENT_RE.search(line)
        if comment_match:
            pending_meta.update(_parse_comment_metadata(comment_match.group(1)))
            i += 1
            continue

        fence_match = _FENCE_OPEN_RE.match(line)
        if fence_match:
            fence = fence_match.group("fence")
            language = fence_match.group("lang").lower()
            open_line = i + 1
            close_re = _closing_fence_re(fence)
            i += 1

            content_lines: list[str] = []
            while i < len(lines):
                if close_re.match(lines[i]):
                    i += 1
                    break
                content_lines.append(lines[i])
                i += 1

            source = "\n".join(content_lines)
            blocks.append(
                CodeBlock(
                    source=source,
                    language=language,
                    line_number=open_line,
                    kind=_classify(source),
                    metadata=pending_meta,
                )
            )
            pending_meta = {}
            continue

        if line.strip():
            pending_meta = {}

        i += 1

    return ParseResult(path=path, blocks=blocks)


def parse_file(path: Path) -> ParseResult:
    """Read *path* and parse it as Markdown.

    Parameters
    ----------
    path:
        Path to a ``.md`` file (or any UTF-8 text file).
    """
    text = path.read_text(encoding="utf-8")
    return parse_text(text, path)
