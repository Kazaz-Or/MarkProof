"""README generator for MarkProof.

Responsibilities
----------------
1. Render three managed sections from live project data:
   - **Architecture** — directory tree, ignoring VCS / build artefacts.
   - **Tech Stack**   — dependencies parsed from ``pyproject.toml``.
   - **Installation** — ``uv sync`` instructions.

2. Wrap every managed section in sentinel HTML comments so it can be
   located and replaced on subsequent runs without touching user prose::

       <!-- markproof:begin:installation -->
       ## Installation
       ...
       <!-- markproof:end:installation -->

3. Expose :class:`ReadmeGenerator` as the primary entry point; a convenience
   function :func:`check_readme` validates an existing README.
"""

from __future__ import annotations

import re
import tomllib
from collections.abc import Callable
from pathlib import Path

from .config import (
    SECTION_ARCHITECTURE,
    SECTION_INSTALLATION,
    SECTION_TECH_STACK,
    MarkProofConfig,
    load_config,
)
from .executor import SnippetExecutor
from .parser import parse_text

# ---------------------------------------------------------------------------
# File-tree helpers
# ---------------------------------------------------------------------------

_IGNORE_NAMES: frozenset[str] = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        ".venv",
        "venv",
        ".env",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "dist",
        "build",
        "node_modules",
        ".tox",
        ".nox",
        # Generated files that would make the tree non-idempotent
        "README.md",
        "CHANGELOG.md",
    }
)


def _should_ignore(path: Path) -> bool:
    name = path.name
    return (
        name in _IGNORE_NAMES
        or name.endswith(".pyc")
        or name.endswith(".egg-info")
        or (name.startswith(".") and name not in {".gitignore", ".python-version"})
    )


def _build_tree(root: Path, prefix: str = "") -> list[str]:
    """Return tree-diagram lines for *root*, sorted dirs-first then files."""
    try:
        children = sorted(
            [p for p in root.iterdir() if not _should_ignore(p)],
            key=lambda p: (p.is_file(), p.name.lower()),
        )
    except PermissionError:
        return []

    lines: list[str] = []
    for idx, child in enumerate(children):
        is_last = idx == len(children) - 1
        connector = "└── " if is_last else "├── "
        suffix = "/" if child.is_dir() else ""
        lines.append(f"{prefix}{connector}{child.name}{suffix}")
        if child.is_dir():
            extension = "    " if is_last else "│   "
            lines.extend(_build_tree(child, prefix + extension))
    return lines


# ---------------------------------------------------------------------------
# Section renderers
# ---------------------------------------------------------------------------


def _parse_pyproject(root: Path) -> dict:  # type: ignore[type-arg]
    """Parse ``pyproject.toml`` in *root*; return empty dict if absent."""
    pyproject = root / "pyproject.toml"
    if not pyproject.exists():
        return {}
    with pyproject.open("rb") as fh:
        return tomllib.load(fh)


def _render_architecture(root: Path) -> str:
    """Render a fenced directory tree under ``## Architecture``."""
    root_name = root.name or root.absolute().name or "project"
    lines = [f"{root_name}/"] + _build_tree(root)
    tree = "\n".join(lines)
    return f"## Architecture\n\n```\n{tree}\n```"


def _render_tech_stack(root: Path) -> str:
    """Render a dependency table + lists under ``## Tech Stack``."""
    data = _parse_pyproject(root)
    project = data.get("project", {})

    python_req = project.get("requires-python", ">=3.12")
    core_deps: list[str] = [
        d for d in project.get("dependencies", []) if isinstance(d, str)
    ]
    dev_deps: list[str] = [
        d
        for group in data.get("dependency-groups", {}).values()
        for d in group
        if isinstance(d, str)
    ]

    parts: list[str] = [
        "## Tech Stack",
        "",
        "| Component | Details |",
        "|-----------|---------|",
        f"| **Python** | `{python_req}` |",
        "| **Package Manager** | [uv](https://docs.astral.sh/uv/) |",
    ]

    if core_deps:
        parts += ["", "**Core Dependencies:**", ""]
        parts += [f"- `{d}`" for d in core_deps]

    if dev_deps:
        parts += ["", "**Dev Dependencies:**", ""]
        parts += [f"- `{d}`" for d in dev_deps]

    return "\n".join(parts)


def _render_installation(root: Path) -> str:
    """Render ``uv sync`` instructions under ``## Installation``."""
    data = _parse_pyproject(root)
    project_name = data.get("project", {}).get("name", root.name or "project")

    return "\n".join(
        [
            "## Installation",
            "",
            "**Prerequisites:** [uv](https://docs.astral.sh/uv/) installed.",
            "",
            "```bash",
            "# Install dependencies",
            "uv sync",
            "```",
            "",
            "For development:",
            "",
            "```bash",
            "uv sync --dev",
            f"uv run {project_name} --help",
            "```",
        ]
    )


# ---------------------------------------------------------------------------
# Section marker helpers
# ---------------------------------------------------------------------------

_SECTION_RENDERERS: dict[str, Callable[[Path], str]] = {
    SECTION_INSTALLATION: _render_installation,
    SECTION_ARCHITECTURE: _render_architecture,
    SECTION_TECH_STACK: _render_tech_stack,
}


def _begin_marker(section_id: str) -> str:
    return f"<!-- markproof:begin:{section_id} -->"


def _end_marker(section_id: str) -> str:
    return f"<!-- markproof:end:{section_id} -->"


def _wrap_section(section_id: str, body: str) -> str:
    """Surround *body* with MarkProof sentinel comments."""
    return f"{_begin_marker(section_id)}\n{body.strip()}\n{_end_marker(section_id)}"


def _update_section(content: str, section_id: str, body: str) -> str:
    """Replace or append a managed section in *content*.

    If the sentinel markers already exist, the content between them is
    replaced in-place.  Otherwise the wrapped section is appended at the end.
    """
    begin = re.escape(_begin_marker(section_id))
    end = re.escape(_end_marker(section_id))
    pattern = re.compile(rf"{begin}.*?{end}", re.DOTALL)

    wrapped = _wrap_section(section_id, body)

    if pattern.search(content):
        return pattern.sub(wrapped, content)

    return content.rstrip("\n") + "\n\n" + wrapped + "\n"


def _section_present(content: str, section_id: str) -> bool:
    """Return True if the begin-marker for *section_id* exists in *content*."""
    return _begin_marker(section_id) in content


# ---------------------------------------------------------------------------
# Check result
# ---------------------------------------------------------------------------


class CheckResult:
    """Outcome of :func:`check_readme`."""

    def __init__(
        self,
        readme_path: Path,
        missing_sections: list[str],
        block_errors: list[str],
    ) -> None:
        self.readme_path = readme_path
        self.missing_sections = missing_sections
        self.block_errors = block_errors

    @property
    def passed(self) -> bool:
        return not self.missing_sections and not self.block_errors


def check_readme(readme_path: Path, config: MarkProofConfig) -> CheckResult:
    """Validate *readme_path* against *config*.

    Checks:
    1. All managed sections have their begin-marker present.
    2. All Python code blocks execute without error.
    """
    if not readme_path.exists():
        return CheckResult(
            readme_path=readme_path,
            missing_sections=list(config.sections.managed),
            block_errors=[f"File not found: {readme_path}"],
        )

    content = readme_path.read_text(encoding="utf-8")

    missing = [
        sid for sid in config.sections.managed if not _section_present(content, sid)
    ]

    parse_result = parse_text(content, readme_path)
    exec_result = SnippetExecutor().execute(parse_result)
    block_errors = [
        f"Line {r.block.line_number}: {r.error}"
        for r in exec_result.results
        if r.error is not None
    ]

    return CheckResult(
        readme_path=readme_path,
        missing_sections=missing,
        block_errors=block_errors,
    )


# ---------------------------------------------------------------------------
# Primary entry point
# ---------------------------------------------------------------------------


class ReadmeGenerator:
    """Scans *root* and generates / updates a ``README.md``.

    Each managed section is written between sentinel comments so subsequent
    runs update only those sections, leaving all other content intact.
    """

    def __init__(self, root: Path, config: MarkProofConfig | None = None) -> None:
        self.root = root
        self.config = config if config is not None else load_config(root)

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def generate(self, output: Path | None = None) -> Path:
        """Write (or update) the README and return its path."""
        readme_path = output or (self.root / self.config.readme.path)

        content = (
            readme_path.read_text(encoding="utf-8")
            if readme_path.exists()
            else self._scaffold_header()
        )

        for section_id in self.config.sections.managed:
            renderer = _SECTION_RENDERERS.get(section_id)
            if renderer is None:
                continue
            body = renderer(self.root)
            content = _update_section(content, section_id, body)

        readme_path.parent.mkdir(parents=True, exist_ok=True)
        readme_path.write_text(content, encoding="utf-8")
        return readme_path

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _scaffold_header(self) -> str:
        """Build the title + description for a brand-new README."""
        data = _parse_pyproject(self.root)
        project = data.get("project", {})
        name = project.get("name", self.root.name or "Project")
        description = project.get("description", "")

        header = f"# {name}\n\n"
        if description:
            header += f"{description}\n\n"
        return header
