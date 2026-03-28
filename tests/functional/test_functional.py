"""Functional tests for MarkProof — CLI-level integration.

Each fixture in ``tests/functional/fixtures/passing/`` must cause
``markproof check`` to exit **0** (all blocks pass, no missing sections).

Each fixture in ``tests/functional/fixtures/failing/`` must cause
``markproof check`` to exit **1** (at least one block raised an exception).

Tests invoke the Typer CLI via ``CliRunner`` — the same path a user or CI
script takes — rather than calling internal Python APIs.  This exercises the
full pipeline: config loading → parse → execute → check result → exit code.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from markproof.cli import app

runner = CliRunner()

_FIXTURES = Path(__file__).parent / "fixtures"

# Docs-style config: no managed sections so check never fails on missing
# markers — only code-block execution errors matter for these fixtures.
_DOCS_CONFIG = "[sections]\nmanaged = []\n"


def _collect(subdir: str) -> list[Path]:
    return sorted((_FIXTURES / subdir).glob("*.md"))


# ---------------------------------------------------------------------------
# Passing fixtures — markproof check must exit 0
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("fixture_path", _collect("passing"), ids=lambda p: p.name)
def test_passing_fixture(fixture_path: Path, tmp_path: Path) -> None:
    """CLI exits 0: every Python block in the fixture runs without error."""
    (tmp_path / "markproof.toml").write_text(_DOCS_CONFIG)
    result = runner.invoke(app, ["check", str(fixture_path), "--root", str(tmp_path)])
    assert result.exit_code == 0, (
        f"{fixture_path.name} — expected exit 0, got {result.exit_code}\n\n"
        f"CLI output:\n{result.output}"
    )


# ---------------------------------------------------------------------------
# Failing fixtures — markproof check must exit 1
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("fixture_path", _collect("failing"), ids=lambda p: p.name)
def test_failing_fixture(fixture_path: Path, tmp_path: Path) -> None:
    """CLI exits 1: at least one Python block in the fixture raises an exception."""
    (tmp_path / "markproof.toml").write_text(_DOCS_CONFIG)
    result = runner.invoke(app, ["check", str(fixture_path), "--root", str(tmp_path)])
    assert result.exit_code == 1, (
        f"{fixture_path.name} — expected exit 1, got {result.exit_code}\n\n"
        f"CLI output:\n{result.output}"
    )
