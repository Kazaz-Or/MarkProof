"""Functional tests driven by fixture Markdown files.

Each fixture in ``tests/fixtures/passing/`` must produce an
``ExecutionResult`` where every non-skipped block passes.

Each fixture in ``tests/fixtures/failing/`` must produce an
``ExecutionResult`` where ``exec_result.passed`` is ``False``.

Per-block behaviour is asserted via metadata annotations:

* ``<!-- markproof:expect_stdout=value -->``
  The block's captured stdout (stripped) must equal *value*.

* ``<!-- markproof:expect_error=ExcType -->``
  The block's ``error`` field must start with *ExcType* (e.g.
  ``"NameError: name 'x' is not defined"`` starts with ``"NameError"``).
"""

from __future__ import annotations

from pathlib import Path

import pytest

# Import at module level to avoid pyfakefs / Pydantic schema issues.
from markproof.executor import SnippetExecutor
from markproof.parser import parse_file

# ---------------------------------------------------------------------------
# Fixture discovery
# ---------------------------------------------------------------------------

_FIXTURES = Path(__file__).parent / "fixtures"


def _collect(subdir: str) -> list[Path]:
    return sorted((_FIXTURES / subdir).glob("*.md"))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _check_block_annotations(
    results: list,  # list[BlockResult]
    *,
    expect_all_pass: bool,
) -> None:
    """Assert per-block metadata annotations and optional global pass check."""
    for br in results:
        if br.skipped:
            continue

        expect_error: str | None = br.block.metadata.get("expect_error")
        expect_stdout: str | None = br.block.metadata.get("expect_stdout")

        if expect_error is not None:
            assert br.error is not None, (
                f"Line {br.block.line_number}: expected {expect_error!r} "
                f"but block succeeded"
            )
            assert br.error.startswith(expect_error), (
                f"Line {br.block.line_number}: expected error starting with "
                f"{expect_error!r}, got {br.error!r}"
            )
        elif expect_all_pass:
            assert br.error is None, (
                f"Line {br.block.line_number}: unexpected error: {br.error}"
            )

        if expect_stdout is not None:
            assert br.stdout.strip() == expect_stdout.strip(), (
                f"Line {br.block.line_number}: expected stdout {expect_stdout!r}, "
                f"got {br.stdout.strip()!r}"
            )


# ---------------------------------------------------------------------------
# Passing fixtures — every non-skipped block must succeed
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path", _collect("passing"), ids=lambda p: p.name)
def test_passing_fixture(path: Path) -> None:
    parse_result = parse_file(path)
    exec_result = SnippetExecutor().execute(parse_result)

    _check_block_annotations(exec_result.results, expect_all_pass=True)
    assert exec_result.passed, (
        f"{path.name} — unexpected failures: {exec_result.errors}"
    )


# ---------------------------------------------------------------------------
# Failing fixtures — at least one non-skipped block must raise an error
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path", _collect("failing"), ids=lambda p: p.name)
def test_failing_fixture(path: Path) -> None:
    parse_result = parse_file(path)
    exec_result = SnippetExecutor().execute(parse_result)

    # Validate any per-block annotations (expect_error / expect_stdout).
    _check_block_annotations(exec_result.results, expect_all_pass=False)

    # The overall result must be a failure.
    assert not exec_result.passed, (
        f"{path.name} — expected at least one block to fail, but all passed"
    )
