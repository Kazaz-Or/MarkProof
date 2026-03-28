# Executor

`executor.py` executes Python code blocks from a `ParseResult` and captures the results.

## Public API

### `SnippetExecutor().execute(parse_result) → ExecutionResult`

Runs every Python block in `parse_result` in document order, returning an `ExecutionResult`.

- Each call to `execute()` starts with a **fresh namespace** — state does not bleed across separate `execute()` calls.
- Within a single call, state is **cumulative**: variables and imports defined in block N are visible in block N+1.
- A failed block does **not** abort the run — all blocks are attempted and their results are recorded.

### `execute_file(path) → ExecutionResult`

Convenience wrapper: parses `path` with `parse_file` then calls `SnippetExecutor().execute()`.

## Skip Logic

A block is skipped (marked `BlockResult.skipped = True`, not executed) when any of these conditions is true:

| Condition | Reason |
|-----------|--------|
| `block.language not in {"python", "python3", "py"}` | Non-Python block |
| `block.kind == INSTALL` | Package installation command |
| `block.metadata.get("skip") == "true"` | Explicit `<!-- markproof:skip -->` annotation |

## Async Detection

Blocks containing top-level `await`, `async for`, or `async with` are detected and wrapped automatically.

Detection strategy:
1. **Fast-path**: if the source contains no `await`/`async for`/`async with` tokens, it is synchronous — no further checks.
2. **Compile probe**: try `compile(source, "<string>", "exec")`. If it succeeds, all async constructs are nested inside `async def` bodies and `exec()` can handle them directly.
3. **SyntaxError → wrap**: a `SyntaxError` means top-level async is present. The source is wrapped in a coroutine.

### Async Wrapper

```python
async def _markproof_async_block():
    # original source, indented
    return dict(locals())
import asyncio as _markproof_asyncio
_markproof_locals = _markproof_asyncio.run(_markproof_async_block())
```

After the event loop finishes, all non-`_` prefixed locals from the coroutine are promoted into the shared namespace so subsequent blocks can reference them.

## Output Capture

`contextlib.redirect_stdout` and `contextlib.redirect_stderr` are used to capture per-block output into `io.StringIO` buffers. Output never escapes to the terminal.

## Data Models

```
ExecutionResult
  └─ path: Path
  └─ results: list[BlockResult]
        ├─ block: CodeBlock
        ├─ stdout: str
        ├─ stderr: str
        ├─ error: str | None   # "ExcType: message", or None on success
        ├─ skipped: bool
        └─ .passed → bool      # True when error is None and not skipped
  └─ .passed → bool            # True when all non-skipped blocks passed
  └─ .errors → list[str]       # error strings for failed blocks
```
