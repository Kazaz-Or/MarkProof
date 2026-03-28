"""Tests for markproof.executor and the execution-result models."""

from pathlib import Path

import pytest

from markproof.executor import (
    SnippetExecutor,
    _execute_source,
    _is_async_source,
    _make_async_wrapper,
    execute_file,
)
from markproof.models import (
    BlockResult,
    CodeBlock,
    CodeBlockKind,
    ExecutionResult,
    ParseResult,
)
from markproof.parser import parse_text


def _make_block(
    source: str,
    language: str = "python",
    kind: CodeBlockKind = CodeBlockKind.USAGE,
    metadata: dict[str, str] | None = None,
    line_number: int = 1,
) -> CodeBlock:
    return CodeBlock(
        source=source,
        language=language,
        line_number=line_number,
        kind=kind,
        metadata=metadata or {},
    )


def _parse(md: str) -> ParseResult:
    return parse_text(md, Path("test.md"))


class TestIsAsyncSource:
    def test_plain_sync_code(self) -> None:
        assert _is_async_source("x = 1\nprint(x)") is False

    def test_empty_string(self) -> None:
        assert _is_async_source("") is False

    def test_no_async_keywords(self) -> None:
        assert _is_async_source("import os\nos.getcwd()") is False

    def test_async_def_only_no_await(self) -> None:
        source = "async def f():\n    pass\n"
        assert _is_async_source(source) is False

    def test_async_def_with_internal_await(self) -> None:
        source = "async def f():\n    await some_coro()\n"
        assert _is_async_source(source) is False

    def test_top_level_await(self) -> None:
        source = "result = await some_coro()"
        assert _is_async_source(source) is True

    def test_top_level_await_in_multiline(self) -> None:
        source = "import asyncio\nasync def f():\n    pass\nresult = await f()"
        assert _is_async_source(source) is True

    def test_async_for_top_level(self) -> None:
        source = "async for item in aiter():\n    print(item)\n"
        assert _is_async_source(source) is True

    def test_async_with_top_level(self) -> None:
        source = "async with ctx() as c:\n    pass\n"
        assert _is_async_source(source) is True

    def test_syntax_error_unrelated_to_async(self) -> None:
        assert _is_async_source("def foo()\n    pass") is False

    def test_await_in_comment_not_detected(self) -> None:
        source = "# await something\nx = 1\n"
        assert _is_async_source(source) is False


class TestMakeAsyncWrapper:
    def test_contains_async_def(self) -> None:
        wrapper = _make_async_wrapper("x = 1")
        assert "async def _markproof_async_block():" in wrapper

    def test_user_code_is_indented(self) -> None:
        wrapper = _make_async_wrapper("x = 1\ny = 2")
        assert "    x = 1" in wrapper
        assert "    y = 2" in wrapper

    def test_contains_return_locals(self) -> None:
        wrapper = _make_async_wrapper("x = 1")
        assert "return dict(locals())" in wrapper

    def test_contains_asyncio_run(self) -> None:
        wrapper = _make_async_wrapper("x = 1")
        assert "asyncio.run(_markproof_async_block())" in wrapper

    def test_result_stored_in_sentinel(self) -> None:
        wrapper = _make_async_wrapper("x = 1")
        assert "_markproof_locals" in wrapper

    def test_multiline_source_preserved(self) -> None:
        source = "a = 1\nb = 2\nc = a + b"
        wrapper = _make_async_wrapper(source)
        assert "    a = 1" in wrapper
        assert "    b = 2" in wrapper
        assert "    c = a + b" in wrapper


class TestExecuteSource:
    def test_stdout_captured(self) -> None:
        ns: dict = {}
        stdout, stderr, error = _execute_source("print('hello')", ns)
        assert stdout == "hello\n"
        assert stderr == ""
        assert error is None

    def test_stderr_captured(self) -> None:
        ns: dict = {}
        source = "import sys\nsys.stderr.write('oops\\n')"
        stdout, stderr, error = _execute_source(source, ns)
        assert stderr == "oops\n"
        assert stdout == ""
        assert error is None

    def test_exception_recorded_as_error(self) -> None:
        ns: dict = {}
        stdout, stderr, error = _execute_source("raise ValueError('bad')", ns)
        assert error is not None
        assert "ValueError" in error
        assert "bad" in error

    def test_name_error_recorded(self) -> None:
        ns: dict = {}
        _, _, error = _execute_source("print(undefined_variable)", ns)
        assert error is not None
        assert "NameError" in error

    def test_syntax_error_recorded(self) -> None:
        ns: dict = {}
        _, _, error = _execute_source("def foo(\n    pass", ns)
        assert error is not None
        assert "SyntaxError" in error

    def test_namespace_mutated_by_assignment(self) -> None:
        ns: dict = {}
        _execute_source("x = 42", ns)
        assert ns["x"] == 42

    def test_cumulative_namespace_across_calls(self) -> None:
        ns: dict = {}
        _execute_source("x = 10", ns)
        _execute_source("y = x * 2", ns)
        assert ns["y"] == 20

    def test_function_defined_and_called_across_calls(self) -> None:
        ns: dict = {}
        _execute_source("def double(n):\n    return n * 2", ns)
        _execute_source("result = double(5)", ns)
        assert ns["result"] == 10

    def test_import_persists_across_calls(self) -> None:
        ns: dict = {}
        _execute_source("import math", ns)
        _execute_source("val = math.pi", ns)
        assert ns["val"] == pytest.approx(3.14159, abs=0.001)

    def test_no_output_no_error(self) -> None:
        ns: dict = {}
        stdout, stderr, error = _execute_source("x = 1 + 1", ns)
        assert stdout == ""
        assert stderr == ""
        assert error is None

    def test_async_block_executes(self) -> None:
        ns: dict = {}
        source = (
            "import asyncio\n"
            "async def work():\n"
            "    await asyncio.sleep(0)\n"
            "    return 99\n"
            "result = await work()\n"
            "print(result)\n"
        )
        stdout, stderr, error = _execute_source(source, ns)
        assert error is None
        assert stdout == "99\n"

    def test_async_locals_promoted_to_namespace(self) -> None:
        ns: dict = {}
        source = (
            "import asyncio\n"
            "async def compute():\n"
            "    await asyncio.sleep(0)\n"
            "    return 7\n"
            "value = await compute()\n"
        )
        _, _, error = _execute_source(source, ns)
        assert error is None
        assert ns["value"] == 7

    def test_async_namespace_visible_in_next_sync_block(self) -> None:
        ns: dict = {}
        source_async = (
            "import asyncio\n"
            "async def get_val():\n"
            "    await asyncio.sleep(0)\n"
            "    return 21\n"
            "val = await get_val()\n"
        )
        _execute_source(source_async, ns)
        _execute_source("doubled = val * 2", ns)
        assert ns["doubled"] == 42

    def test_async_stdout_captured(self) -> None:
        ns: dict = {}
        source = (
            "import asyncio\n"
            "async def say():\n"
            "    await asyncio.sleep(0)\n"
            "    print('async says hi')\n"
            "await say()\n"
        )
        stdout, _, error = _execute_source(source, ns)
        assert error is None
        assert "async says hi" in stdout

    def test_async_exception_recorded(self) -> None:
        ns: dict = {}
        source = (
            "import asyncio\n"
            "async def boom():\n"
            "    raise RuntimeError('async fail')\n"
            "await boom()\n"
        )
        _, _, error = _execute_source(source, ns)
        assert error is not None
        assert "RuntimeError" in error
        assert "async fail" in error

    def test_async_wrapper_artefacts_cleaned_up(self) -> None:
        ns: dict = {}
        source = (
            "import asyncio\nx = await asyncio.coroutine(lambda: None)()\n"
            if False
            else "import asyncio\nval = await asyncio.sleep(0) or 5\n"
        )
        _execute_source(source, ns)
        assert "_markproof_async_block" not in ns
        assert "_markproof_asyncio" not in ns
        assert "_markproof_locals" not in ns


class TestRunBlockSkipLogic:
    def _executor_run_one(self, block: CodeBlock) -> BlockResult:
        pr = ParseResult(path=Path("x.md"), blocks=[block])
        return SnippetExecutor().execute(pr).results[0]

    def test_bash_block_skipped(self) -> None:
        block = _make_block("pip install foo", language="bash")
        result = self._executor_run_one(block)
        assert result.skipped is True

    def test_shell_block_skipped(self) -> None:
        block = _make_block("echo hello", language="sh")
        result = self._executor_run_one(block)
        assert result.skipped is True

    def test_unlabelled_block_skipped(self) -> None:
        block = _make_block("x = 1", language="")
        result = self._executor_run_one(block)
        assert result.skipped is True

    def test_install_kind_skipped(self) -> None:
        block = _make_block(
            "pip install x", language="python", kind=CodeBlockKind.INSTALL
        )
        result = self._executor_run_one(block)
        assert result.skipped is True

    def test_skip_metadata_flag(self) -> None:
        block = _make_block("raise RuntimeError", metadata={"skip": "true"})
        result = self._executor_run_one(block)
        assert result.skipped is True
        assert result.error is None

    def test_python_label_executes(self) -> None:
        block = _make_block("x = 1")
        result = self._executor_run_one(block)
        assert result.skipped is False
        assert result.passed is True

    def test_python3_label_executes(self) -> None:
        block = _make_block("x = 1", language="python3")
        result = self._executor_run_one(block)
        assert result.skipped is False
        assert result.passed is True

    def test_py_label_executes(self) -> None:
        block = _make_block("x = 1", language="py")
        result = self._executor_run_one(block)
        assert result.skipped is False
        assert result.passed is True

    def test_skip_false_metadata_does_not_skip(self) -> None:
        block = _make_block("x = 1", metadata={"skip": "false"})
        result = self._executor_run_one(block)
        assert result.skipped is False


class TestBlockResult:
    def test_passed_no_error_not_skipped(self) -> None:
        block = _make_block("x = 1")
        r = BlockResult(block=block)
        assert r.passed is True

    def test_not_passed_when_error(self) -> None:
        block = _make_block("x = 1")
        r = BlockResult(block=block, error="ValueError: oops")
        assert r.passed is False

    def test_not_passed_when_skipped(self) -> None:
        block = _make_block("x = 1")
        r = BlockResult(block=block, skipped=True)
        assert r.passed is False

    def test_stdout_and_stderr_default_empty(self) -> None:
        block = _make_block("x = 1")
        r = BlockResult(block=block)
        assert r.stdout == ""
        assert r.stderr == ""


class TestExecutionResult:
    def _result_from_blocks(self, *block_results: BlockResult) -> ExecutionResult:
        return ExecutionResult(path=Path("x.md"), results=list(block_results))

    def test_passed_when_all_pass(self) -> None:
        b = _make_block("x = 1")
        er = self._result_from_blocks(BlockResult(block=b))
        assert er.passed is True

    def test_passed_with_skipped_blocks(self) -> None:
        b = _make_block("x = 1")
        er = self._result_from_blocks(BlockResult(block=b, skipped=True))
        assert er.passed is True

    def test_not_passed_when_any_error(self) -> None:
        b = _make_block("x = 1")
        er = self._result_from_blocks(
            BlockResult(block=b),
            BlockResult(block=b, error="ValueError: oops"),
        )
        assert er.passed is False

    def test_errors_property_filters_correctly(self) -> None:
        b = _make_block("x = 1")
        good = BlockResult(block=b)
        bad = BlockResult(block=b, error="TypeError: nope")
        skipped = BlockResult(block=b, skipped=True)
        er = self._result_from_blocks(good, bad, skipped)
        assert er.errors == [bad]

    def test_errors_empty_when_all_pass(self) -> None:
        b = _make_block("x = 1")
        er = self._result_from_blocks(BlockResult(block=b))
        assert er.errors == []

    def test_passed_empty_result_list(self) -> None:
        er = ExecutionResult(path=Path("x.md"))
        assert er.passed is True


class TestSnippetExecutorIntegration:
    def test_path_propagated_to_result(self) -> None:
        pr = _parse("")
        er = SnippetExecutor().execute(pr)
        assert er.path == Path("test.md")

    def test_empty_document(self) -> None:
        er = SnippetExecutor().execute(_parse(""))
        assert er.results == []
        assert er.passed is True

    def test_install_block_skipped(self) -> None:
        md = "```bash\npip install requests\n```\n"
        er = SnippetExecutor().execute(_parse(md))
        assert er.results[0].skipped is True

    def test_single_block_passes(self) -> None:
        md = "```python\nx = 1 + 1\n```\n"
        er = SnippetExecutor().execute(_parse(md))
        assert len(er.results) == 1
        assert er.results[0].passed is True

    def test_stdout_captured_per_block(self) -> None:
        md = "```python\nprint('hi')\n```\n"
        er = SnippetExecutor().execute(_parse(md))
        assert er.results[0].stdout == "hi\n"

    def test_error_block_recorded_not_aborted(self) -> None:
        md = (
            "```python\nraise ValueError('first')\n```\n"
            "```python\nprint('second')\n```\n"
        )
        er = SnippetExecutor().execute(_parse(md))
        assert er.results[0].error is not None
        assert er.results[1].stdout == "second\n"

    def test_each_execute_call_gets_fresh_namespace(self) -> None:
        executor = SnippetExecutor()
        md = "```python\nx = 99\n```\n"
        er1 = executor.execute(_parse(md))
        md2 = "```python\nprint(x)\n```\n"
        er2 = executor.execute(_parse(md2))
        assert er1.results[0].passed is True
        assert er2.results[0].error is not None

    def test_skip_annotated_block(self) -> None:
        md = "<!-- markproof:skip -->\n```python\nraise RuntimeError\n```\n"
        er = SnippetExecutor().execute(_parse(md))
        assert er.results[0].skipped is True
        assert er.passed is True

    def test_multistep_tutorial_cumulative_state(self) -> None:
        md = """
# Tutorial

## Install

```bash
pip install somelib
```

## Step 1 – define a helper

```python
def greet(name: str) -> str:
    return f"Hello, {name}!"
```

## Step 2 – call the helper

```python
message = greet("World")
print(message)
```

## Step 3 – use cumulative variable

```python
import math
length = len(message)
root = math.floor(math.sqrt(length))
print(root)
```
""".strip()

        er = SnippetExecutor().execute(_parse(md))

        assert er.results[0].skipped is True
        assert er.results[1].passed is True
        assert er.results[1].stdout == ""
        assert er.results[2].passed is True
        assert er.results[2].stdout == "Hello, World!\n"
        assert er.results[3].passed is True
        assert er.results[3].stdout == "3\n"
        assert er.passed is True

    def test_async_single_block(self) -> None:
        md = (
            "```python\n"
            "import asyncio\n"
            "async def add(a: int, b: int) -> int:\n"
            "    await asyncio.sleep(0)\n"
            "    return a + b\n"
            "total = await add(3, 4)\n"
            "print(total)\n"
            "```\n"
        )
        er = SnippetExecutor().execute(_parse(md))
        assert er.results[0].passed is True
        assert er.results[0].stdout == "7\n"

    def test_async_variable_visible_in_next_sync_block(self) -> None:
        md = (
            "```python\n"
            "import asyncio\n"
            "async def get_base() -> int:\n"
            "    await asyncio.sleep(0)\n"
            "    return 10\n"
            "base = await get_base()\n"
            "```\n"
            "\n"
            "```python\n"
            "print(base * 3)\n"
            "```\n"
        )
        er = SnippetExecutor().execute(_parse(md))
        assert er.results[0].passed is True
        assert er.results[1].passed is True
        assert er.results[1].stdout == "30\n"

    def test_async_function_defined_then_awaited_in_next_block(self) -> None:
        """Async function defined in block 1, awaited at top-level in block 2."""
        md = (
            "```python\n"
            "import asyncio\n"
            "\n"
            "async def compute(n: int) -> int:\n"
            "    await asyncio.sleep(0)\n"
            "    return n ** 2\n"
            "```\n"
            "\n"
            "```python\n"
            "result = await compute(6)\n"
            "print(result)\n"
            "```\n"
        )
        er = SnippetExecutor().execute(_parse(md))
        assert er.results[0].passed is True
        assert er.results[1].passed is True
        assert er.results[1].stdout == "36\n"

    def test_full_async_tutorial(self) -> None:
        """End-to-end tutorial: install, sync setup, async usage, sync teardown."""
        md = """
# Async Tutorial

## Install

```bash
pip install asyncio
```

## Define async utilities

```python
import asyncio

async def fetch_data(value: int) -> dict:
    await asyncio.sleep(0)
    return {"value": value, "doubled": value * 2}
```

## Fetch and print

```python
data = await fetch_data(21)
print(data["doubled"])
```

## Verify synchronously

```python
assert data["value"] == 21
print("ok")
```
""".strip()

        er = SnippetExecutor().execute(_parse(md))

        assert er.results[0].skipped is True
        assert er.results[1].passed is True
        assert er.results[2].passed is True
        assert er.results[2].stdout == "42\n"
        assert er.results[3].passed is True
        assert er.results[3].stdout == "ok\n"
        assert er.passed is True

    def test_execute_file_end_to_end(self, fs) -> None:  # noqa: ANN001
        content = "```python\nx = 6\ny = 7\n```\n```python\nprint(x * y)\n```\n"
        fs.create_file("/docs/readme.md", contents=content)
        er = execute_file(Path("/docs/readme.md"))
        assert er.passed is True
        assert er.results[1].stdout == "42\n"
