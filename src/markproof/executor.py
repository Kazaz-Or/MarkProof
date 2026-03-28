"""Snippet executor for MarkProof.

Responsibilities
----------------
1. Execute Python code blocks from a ``ParseResult`` cumulatively — imports
   and variables defined in earlier blocks are visible in later ones.
2. Capture stdout and stderr per block without letting them escape to the
   terminal.
3. Detect top-level ``await`` / ``async for`` / ``async with`` usage and
   transparently wrap those blocks in an async runner so they execute
   correctly inside a plain ``exec()`` call.
4. Honour ``<!-- markproof:skip -->`` metadata and skip non-Python /
   INSTALL blocks automatically.
"""

from __future__ import annotations

import contextlib
import io
import re
import textwrap
from pathlib import Path

from .models import (
    BlockResult,
    CodeBlock,
    CodeBlockKind,
    ExecutionResult,
    ParseResult,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Language tags that we treat as Python source.
_PYTHON_LANGS: frozenset[str] = frozenset({"python", "python3", "py"})

# Matches any use of await at expression level, or async-for / async-with
# at statement level.  Used as a fast pre-filter before attempting compile().
_ASYNC_USAGE_RE = re.compile(
    r"\bawait\b|\basync\s+(?:for|with)\b",
    re.MULTILINE,
)


# ---------------------------------------------------------------------------
# Async detection helpers
# ---------------------------------------------------------------------------


def _is_async_source(source: str) -> bool:
    """Return ``True`` if *source* contains top-level async constructs.

    Strategy
    --------
    1. Fast-path: if the source has no ``await`` / ``async for`` /
       ``async with`` tokens at all, it is definitely synchronous.
    2. Try to compile the source normally.  If that succeeds the async
       constructs are all safely inside ``async def`` bodies — no wrapper
       is needed.
    3. If compilation raises ``SyntaxError``, it means there is a
       top-level await/async-for/async-with that ``exec()`` cannot handle
       directly → signal that wrapping is required.
    """
    if not _ASYNC_USAGE_RE.search(source):
        return False
    try:
        compile(source, "<string>", "exec")
        return False  # compiled fine: async constructs are nested inside functions
    except SyntaxError:
        return True  # top-level async construct found


def _make_async_wrapper(source: str) -> str:
    """Wrap *source* in a coroutine that captures and returns its locals.

    The generated code:

    1. Defines ``_markproof_async_block`` as an ``async def`` containing
       the original *source* followed by ``return dict(locals())``.
    2. Runs it with ``asyncio.run()``.
    3. Stores the returned locals dict in ``_markproof_locals`` so the
       caller can promote them back into the shared namespace.
    """
    indented = textwrap.indent(source, "    ")
    return (
        "async def _markproof_async_block():\n"
        f"{indented}\n"
        "    return dict(locals())\n"
        "import asyncio as _markproof_asyncio\n"
        "_markproof_locals = _markproof_asyncio.run(_markproof_async_block())\n"
    )


# ---------------------------------------------------------------------------
# Core execution helper
# ---------------------------------------------------------------------------


def _execute_source(
    source: str,
    namespace: dict,  # type: ignore[type-arg]
) -> tuple[str, str, str | None]:
    """Exec *source* inside *namespace*, capturing I/O.

    Returns
    -------
    ``(stdout, stderr, error)`` where *error* is ``None`` on success or a
    ``"ExcType: message"`` string when an exception is raised.

    Side-effects
    ------------
    *namespace* is mutated: new names defined by *source* are added to it so
    subsequent blocks can reference them (cumulative execution).  For async
    blocks the coroutine-local names are promoted into *namespace* after the
    event loop finishes.
    """
    stdout_buf = io.StringIO()
    stderr_buf = io.StringIO()
    error: str | None = None

    is_async = _is_async_source(source)
    code = _make_async_wrapper(source) if is_async else source

    try:
        with (
            contextlib.redirect_stdout(stdout_buf),
            contextlib.redirect_stderr(stderr_buf),
        ):
            exec(code, namespace)  # noqa: S102

        if is_async:
            # Pull local variables from the coroutine back into the shared
            # namespace so future blocks can see them.
            async_locals: dict = namespace.pop("_markproof_locals", None) or {}  # type: ignore[type-arg]
            namespace.update(
                {k: v for k, v in async_locals.items() if not k.startswith("_")}
            )
            # Clean up wrapper artefacts.
            namespace.pop("_markproof_async_block", None)
            namespace.pop("_markproof_asyncio", None)

    except Exception as exc:  # noqa: BLE001
        error = f"{type(exc).__name__}: {exc}"

    return stdout_buf.getvalue(), stderr_buf.getvalue(), error


# ---------------------------------------------------------------------------
# Public executor
# ---------------------------------------------------------------------------


class SnippetExecutor:
    """Executes all Python blocks in a :class:`~markproof.models.ParseResult`.

    Each call to :meth:`execute` starts with a **fresh** namespace, so blocks
    accumulate state only *within* a single document execution.  Subsequent
    calls to ``execute()`` are independent of one another.
    """

    def execute(self, parse_result: ParseResult) -> ExecutionResult:
        """Run every block in *parse_result* and return the aggregated results.

        Blocks are executed in document order.  A failed block does **not**
        abort the run — all remaining blocks are attempted so the caller gets
        a complete picture of what passed and what failed.
        """
        namespace: dict = {}  # type: ignore[type-arg]
        result = ExecutionResult(path=parse_result.path)
        for block in parse_result.blocks:
            result.results.append(self._run_block(block, namespace))
        return result

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _run_block(
        self,
        block: CodeBlock,
        namespace: dict,  # type: ignore[type-arg]
    ) -> BlockResult:
        """Decide whether to skip or execute a single block."""
        # Skip non-Python code (bash, shell, unlabelled, …).
        if block.language not in _PYTHON_LANGS:
            return BlockResult(block=block, skipped=True)

        # Skip package-installation blocks (pip install …).
        if block.kind == CodeBlockKind.INSTALL:
            return BlockResult(block=block, skipped=True)

        # Honour explicit <!-- markproof:skip --> annotation.
        if block.metadata.get("skip") == "true":
            return BlockResult(block=block, skipped=True)

        stdout, stderr, error = _execute_source(block.source, namespace)
        return BlockResult(
            block=block,
            stdout=stdout,
            stderr=stderr,
            error=error,
        )


def execute_file(path: Path) -> ExecutionResult:
    """Convenience wrapper: parse *path* then execute all its Python blocks."""
    from .parser import parse_file  # local import to avoid circularity

    parse_result = parse_file(path)
    return SnippetExecutor().execute(parse_result)
