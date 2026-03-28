<div align="center">

<img src="assets/markproof.png" alt="MarkProof" width="180" />

# MarkProof

**Validate that your documentation actually works.**

![Python](https://img.shields.io/badge/python-3.12+-blue.svg)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
![License](https://img.shields.io/badge/license-MIT-green.svg)

</div>

MarkProof is a CLI tool that executes embedded Python code blocks in Markdown files and enforces that managed README sections stay in sync with the source tree. If your docs raise an exception, the build fails.

Write once, verify continuously — documentation that lies is worse than no documentation at all.

---

## Table of Contents

- [Why MarkProof](#why-markproof)
- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Commands](#commands)
- [Metadata Annotations](#metadata-annotations)
- [Configuration](#configuration)
- [How It Works](#how-it-works)
- [Examples](#examples)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Development](#development)
- [License](#license)

---

## Why MarkProof

Documentation drifts. A README written today shows a function signature from last month, a configuration key that was renamed, or an example that raises an `ImportError` on the current version. Teams notice this at the worst possible moment — when a new contributor follows the instructions and they fail.

MarkProof treats your docs as tests: if the code in your README doesn't run, the CI pipeline breaks. Managed sections (architecture tree, dependency table, installation commands) are regenerated from live data on every run so they never go stale.

---

## Features

- **Execute code blocks** — runs every Python block in a Markdown file cumulatively, preserving imports and variables across blocks just like a real tutorial
- **Async support** — top-level `await`, `async for`, and `async with` are detected and transparently wrapped in an event loop; no changes to your code blocks required
- **Managed sections** — `architecture`, `tech_stack`, and `installation` sections are rendered from live project data (`pyproject.toml`, directory listing) and kept in sync on every run
- **Surgical updates** — sentinel HTML comments mark managed regions; all surrounding prose is left untouched
- **Skip annotations** — individual blocks can be excluded from execution with `<!-- markproof:skip -->`
- **Never aborts** — a failing block records its error and the executor moves on; you get a complete picture of every failure in one run
- **Zero configuration** — all defaults work out of the box; `markproof.toml` is fully optional

---

<!-- markproof:begin:installation -->
## Installation

**From PyPI** (recommended):

```bash
pip install markproof
# or with uv
uv tool install markproof
```

**Add to a project** (as a dev dependency):

```bash
uv add --dev markproof
```

**For development** (clone + install from source):

**Prerequisites:** [uv](https://docs.astral.sh/uv/) installed.

```bash
uv sync --dev
uv run markproof --help
```
<!-- markproof:end:installation -->

---

## Quick Start

```bash
# Generate (or refresh) your README from the current source tree
markproof generate .

# Validate the README — fails if any section is missing or any Python block errors
markproof check README.md --root .
```

Add a check step to CI and documentation accuracy becomes a build requirement.

**With the GitHub Action** (simplest):

```yaml
- uses: actions/checkout@v4

- name: Validate README
  uses: Kazaz-Or/MarkProof@v1
  with:
    path: README.md
    root: '.'
    generate: 'true'   # regenerate managed sections before checking
```

**Or directly with uv**:

```yaml
- name: Regenerate README
  run: uv run markproof generate .

- name: Validate README
  run: uv run markproof check README.md --root .
```

---

## Commands

### `generate`

Scans the project root, renders all managed sections from live data, and writes
(or updates) the README. If the file does not exist it is created with a title
and description scaffolded from `pyproject.toml`.

```
markproof generate [ROOT] [--output PATH]
```

| Argument | Default | Description |
|----------|---------|-------------|
| `ROOT` | `.` | Project root directory |
| `--output PATH` | value of `readme.path` in config | Override the output path |

Running `generate` twice produces identical output — the command is fully idempotent.

### `check`

Validates an existing Markdown file against the project configuration. Reports
missing managed-section markers and Python blocks that raise exceptions.

```
markproof check PATH [--root ROOT]
```

| Argument | Default | Description |
|----------|---------|-------------|
| `PATH` | *(required)* | Markdown file to validate |
| `--root ROOT` | `.` | Project root for loading `markproof.toml` |

Exit codes: `0` on success, `1` on any failure.

---

## Metadata Annotations

Control execution behaviour on a per-block basis using HTML comments placed
immediately before a fenced code block. Blank lines between a comment and its
block are fine; any non-blank, non-comment line resets the annotation.

```markdown
<!-- markproof:skip -->
```python
# this block will not be executed
raise RuntimeError("unreachable")
```
```

| Annotation | Effect |
|------------|--------|
| `<!-- markproof:skip -->` | Block is excluded from execution entirely |
| `<!-- markproof:expect_stdout=value -->` | Functional-test assertion: captured stdout must equal *value* |
| `<!-- markproof:expect_error=ExcType -->` | Functional-test assertion: block must raise an exception whose type name starts with *ExcType* |

Multiple tokens can appear in a single comment:

```markdown
<!-- markproof:expect_error=ValueError id=example-3 -->
```python
int("not a number")
```
```

---

## Configuration

MarkProof is configured via `markproof.toml` in the project root. The file is
entirely optional — every field has a sensible default.

```toml
[readme]
path = "README.md"           # README path, relative to the project root

[sections]
managed = [                  # sections MarkProof will generate and keep current
    "installation",
    "architecture",
    "tech_stack",
]
```

### Built-in section IDs

| ID | Heading | Source |
|----|---------|--------|
| `installation` | `## Installation` | Static `uv sync` instructions |
| `architecture` | `## Architecture` | Live directory tree |
| `tech_stack` | `## Tech Stack` | `pyproject.toml` dependencies |

Set `managed = []` to use MarkProof purely as a code-block executor without
any automatic section management.

### Docs-directory config

Sub-directories that contain only documentation (no managed README) can carry
their own `markproof.toml` to suppress section checks:

```toml
# docs/markproof.toml
[sections]
managed = []
```

---

## How It Works

MarkProof runs as a linear pipeline:

```
Markdown file
      │
      ▼  parse_text()
 ParseResult
   └─ list[CodeBlock]  ─ source, language, line_number, kind, metadata
      │
      ▼  SnippetExecutor().execute()
 ExecutionResult
   └─ list[BlockResult]  ─ stdout, stderr, error, skipped
      │
      ├──▶  check_readme()     →  CheckResult  (validates existing README)
      └──▶  ReadmeGenerator    →  writes/updates README.md
```

All Python blocks in a single `execute()` call share one namespace — imports
and variables defined in block N are visible in block N+1. A failed block never
aborts the run; all remaining blocks are attempted.

**Async blocks** are detected in two steps:

1. Fast-path: if the source has no `await` / `async for` / `async with` tokens
   it is synchronous.
2. Compile probe: if the tokens are present but `compile()` succeeds, they are
   safely nested inside `async def` bodies — no wrapper needed.
3. `SyntaxError` means top-level async — the block is wrapped in a coroutine,
   run with `asyncio.run()`, and its locals promoted back to the shared namespace.

**Managed sections** are wrapped in sentinel comments:

```html
<!-- markproof:begin:installation -->
## Installation

**From PyPI** (recommended):

```bash
pip install markproof
# or with uv
uv tool install markproof
```

**Add to a project** (as a dev dependency):

```bash
uv add --dev markproof
```

**For development** (clone + install from source):

**Prerequisites:** [uv](https://docs.astral.sh/uv/) installed.

```bash
uv sync --dev
uv run markproof --help
```
<!-- markproof:end:installation -->
```

`generate` uses a `re.DOTALL` substitution to replace only the content between
the markers, leaving all prose outside them untouched.

---

## Examples

The [`examples/`](examples/) directory contains self-contained projects that
demonstrate MarkProof's features. Each has its own `markproof.toml` with
`managed = []` so you can run checks without needing a full project scaffold.

| Example | What it covers |
|---------|---------------|
| [`getting_started/`](examples/getting_started/) | Basic execution, `expect_stdout`, `expect_error`, `skip`, cumulative state |
| [`data_pipeline/`](examples/data_pipeline/) | CSV parsing pipeline with stdout assertions across multiple blocks |
| [`async_api_client/`](examples/async_api_client/) | Top-level `await`, simulated network calls, error surface documentation |

Run any example:

```bash
markproof check examples/getting_started/README.md --root examples/getting_started
```

---

<!-- markproof:begin:architecture -->
## Architecture

```
MarkProof/
├── docs/
│   ├── architecture.md
│   ├── configuration.md
│   ├── executor.md
│   ├── generator.md
│   ├── markproof.toml
│   └── parser.md
├── src/
│   └── markproof/
│       ├── __init__.py
│       ├── _version.py
│       ├── cli.py
│       ├── config.py
│       ├── executor.py
│       ├── generator.py
│       ├── models.py
│       └── parser.py
├── tests/
│   ├── functional/
│   │   ├── fixtures/
│   │   │   ├── failing/
│   │   │   │   ├── 01_name_error.md
│   │   │   │   ├── 02_type_error.md
│   │   │   │   ├── 03_assertion_error.md
│   │   │   │   ├── 04_import_error.md
│   │   │   │   └── 05_continues_after_error.md
│   │   │   └── passing/
│   │   │       ├── 01_simple_print.md
│   │   │       ├── 02_cumulative_state.md
│   │   │       ├── 03_function_across_blocks.md
│   │   │       ├── 04_import_persistence.md
│   │   │       ├── 05_skip_annotated.md
│   │   │       ├── 06_install_blocks_skipped.md
│   │   │       ├── 07_async_await.md
│   │   │       └── 08_mixed_languages.md
│   │   ├── __init__.py
│   │   └── test_functional.py
│   ├── unit/
│   │   ├── __init__.py
│   │   ├── test_cli.py
│   │   ├── test_executor.py
│   │   ├── test_generator.py
│   │   └── test_parser.py
│   └── __init__.py
├── .gitignore
├── CLAUDE.md
├── LICENSE
├── Makefile
├── markproof.toml
├── pyproject.toml
└── uv.lock
```
<!-- markproof:end:architecture -->

---

<!-- markproof:begin:tech_stack -->
## Tech Stack

| Component | Details |
|-----------|---------|
| **Python** | `>=3.12` |
| **Package Manager** | [uv](https://docs.astral.sh/uv/) |

**Core Dependencies:**

- `httpx>=0.27`
- `typer>=0.12`
- `pydantic>=2.0`
- `rich>=13.0`

**Dev Dependencies:**

- `pytest>=8.0`
- `pyfakefs>=5.0`
- `ruff>=0.4`
<!-- markproof:end:tech_stack -->

---

## Development

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) — install with `curl -LsSf https://astral.sh/uv/install.sh | sh`

### Setup

```bash
git clone https://github.com/Kazaz-Or/MarkProof.git
cd MarkProof
make dev
```

### Common Tasks

All development workflows are available via `make`:

```
make help              show all available targets

make test              run the full test suite (unit + functional)
make test-unit         run unit tests only
make test-functional   run functional tests only

make fix               apply ruff lint fixes and auto-format
make check             lint + format check (no writes, CI-safe)

make generate          regenerate README from the current source tree
make docs-check        validate README and every page in docs/

make ci                full pipeline: fix → test → generate → docs-check
make clean             remove __pycache__, .pytest_cache, .ruff_cache, dist
```

### Test Layout

```
tests/
├── unit/                     isolated tests with pyfakefs — no real I/O
│   ├── test_parser.py        parser, model contracts, metadata parsing
│   ├── test_executor.py      execution, async detection, skip logic
│   ├── test_generator.py     section rendering, tree builder, check_readme
│   └── test_cli.py           Typer CLI commands via CliRunner
└── functional/               end-to-end tests driven by fixture Markdown files
    ├── test_functional.py    parametrised runner — reads expect_* annotations
    └── fixtures/
        ├── passing/          each file must yield ExecutionResult.passed == True
        └── failing/          each file must yield ExecutionResult.passed == False
```

To add a scenario, drop a `.md` file into `passing/` or `failing/` and annotate
blocks with `<!-- markproof:expect_stdout=… -->` or
`<!-- markproof:expect_error=… -->`. No test code changes required.

### Adding a Managed Section

1. Add a renderer `_render_my_section(root: Path) -> str` in `generator.py`.
2. Register it in `_SECTION_RENDERERS`.
3. Add a constant to `config.py` and append it to `ALL_SECTIONS`.
4. Include the new ID in `markproof.toml` under `sections.managed`.

---

## License

[MIT](LICENSE)
