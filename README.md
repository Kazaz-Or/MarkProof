# MarkProof

<!-- markproof:begin:installation -->
## Installation

**Prerequisites:** [uv](https://docs.astral.sh/uv/) installed.

```bash
# Install dependencies
uv sync
```

For development:

```bash
uv sync --dev
uv run markproof --help
```
<!-- markproof:end:installation -->

<!-- markproof:begin:architecture -->
## Architecture

```
MarkProof/
├── src/
│   └── markproof/
│       ├── __init__.py
│       ├── cli.py
│       ├── config.py
│       ├── executor.py
│       ├── generator.py
│       ├── models.py
│       └── parser.py
├── tests/
│   ├── __init__.py
│   ├── test_cli.py
│   ├── test_executor.py
│   ├── test_generator.py
│   └── test_parser.py
├── .gitignore
├── CLAUDE.md
├── LICENSE
├── markproof.toml
├── pyproject.toml
└── uv.lock
```
<!-- markproof:end:architecture -->

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
