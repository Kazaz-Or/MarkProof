# Generator

`generator.py` renders managed README sections from live project data and updates them in-place.

## Public API

### `ReadmeGenerator(root, config=None)`

Main entry point. Scans `root` and generates / updates the README.

| Parameter | Type | Description |
|-----------|------|-------------|
| `root` | `Path` | Project root directory |
| `config` | `MarkProofConfig \| None` | Config to use; loaded from `markproof.toml` if omitted |

#### `.generate(output=None) → Path`

Writes (or updates) the README and returns its path. If the file does not exist, a header scaffold is written first. For each managed section, the corresponding renderer is called and the content is inserted between sentinel markers.

### `check_readme(readme_path, config) → CheckResult`

Validates an existing README. Checks:
1. All managed sections have their `<!-- markproof:begin:X -->` marker present.
2. All Python code blocks execute without raising an exception.

Returns a `CheckResult` with `.passed`, `.missing_sections`, and `.block_errors`.

## Managed Sections

| Section ID | Heading | Content |
|------------|---------|---------|
| `installation` | `## Installation` | `uv sync` commands |
| `architecture` | `## Architecture` | Directory tree |
| `tech_stack` | `## Tech Stack` | Dependency table from `pyproject.toml` |

Sections not present in `config.sections.managed` are ignored.

## Sentinel Markers

Every managed section is wrapped in HTML comment sentinels:

```html
<!-- markproof:begin:installation -->
## Installation
…
<!-- markproof:end:installation -->
```

`_update_section()` uses a `re.DOTALL` substitution to replace only the content between the markers, leaving all surrounding prose untouched. If the markers are absent, the wrapped section is appended at the end of the file.

## File Tree

The architecture section renders a directory tree using `_build_tree()`.

**Ignored by default:**

| Category | Names |
|----------|-------|
| VCS | `.git`, `.hg`, `.svn` |
| Virtualenvs | `.venv`, `venv`, `.env` |
| Caches | `__pycache__`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache` |
| Build artefacts | `dist`, `build`, `node_modules`, `.tox`, `.nox` |
| Generated docs | `README.md`, `CHANGELOG.md` |
| File patterns | `*.pyc`, `*.egg-info`, dotfiles (except `.gitignore`, `.python-version`) |

`README.md` and `CHANGELOG.md` are excluded so that regenerating the README does not change the tree on the next run (idempotency guarantee).

## Idempotency

Running `markproof generate .` twice in a row produces identical output because:
- The tree scan excludes the output file.
- Section content is rendered from static sources (`pyproject.toml`, directory listing).
- `_update_section` replaces existing markers rather than appending duplicates.
