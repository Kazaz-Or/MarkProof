# Architecture

MarkProof is structured as a linear pipeline: **parse → execute → check / generate**.

## Module Map

| Module | Responsibility |
|--------|---------------|
| `models.py` | Shared data models (`CodeBlock`, `ParseResult`, `BlockResult`, `ExecutionResult`) |
| `parser.py` | Extract fenced code blocks and `<!-- markproof:… -->` metadata from Markdown |
| `executor.py` | Execute Python blocks cumulatively; capture stdout/stderr; wrap async code |
| `config.py` | Load and validate `markproof.toml` via Pydantic |
| `generator.py` | Render managed README sections; update in-place via sentinel markers |
| `cli.py` | Typer-based entry point (`generate`, `check`) |

## Data Flow

```
Markdown text / file
        │
        ▼
  parser.parse_text()
        │  ParseResult
        │    └─ list[CodeBlock]
        │         ├─ source, language, line_number
        │         ├─ kind  (INSTALL | USAGE)
        │         └─ metadata  {key: value, …}
        ▼
  executor.SnippetExecutor().execute()
        │  ExecutionResult
        │    └─ list[BlockResult]
        │         ├─ stdout, stderr
        │         ├─ error  (None on success)
        │         └─ skipped
        ▼
  generator.check_readme()   ─── or ───  generator.ReadmeGenerator.generate()
       CheckResult                              writes README.md
```

## Key Invariants

1. **Cumulative namespace** — all Python blocks in one `execute()` call share a
   single `dict`.  A variable defined in block 2 is visible in block 3.

2. **Never abort** — the executor catches all exceptions and records them as
   `BlockResult.error`.  All blocks are attempted regardless of earlier failures.

3. **Idempotent generation** — running `markproof generate .` twice produces
   identical output because `README.md` and `CHANGELOG.md` are excluded from
   the architecture tree scan.

4. **Section markers are surgical** — `_update_section()` uses a `re.DOTALL`
   substitution to replace only the content between
   `<!-- markproof:begin:X -->` … `<!-- markproof:end:X -->` markers, leaving
   all surrounding prose untouched.

## Dependency Graph

```
cli.py
  ├── config.py          (load markproof.toml)
  └── generator.py
        ├── config.py
        ├── executor.py
        │     └── models.py
        └── parser.py
              └── models.py
```

`config.py` and `models.py` have no intra-package dependencies.
