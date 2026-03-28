# Configuration

MarkProof is configured via a `markproof.toml` file in the project root. Every field has a default so the file is entirely optional.

## Full Example

```toml
[readme]
path = "README.md"

[sections]
managed = ["installation", "architecture", "tech_stack"]
```

## `[readme]`

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `path` | string | `"README.md"` | Path to the README, relative to the project root |

## `[sections]`

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `managed` | list of strings | all three built-in sections | Section IDs that MarkProof will generate and keep up-to-date |

### Built-in Section IDs

| ID | Description |
|----|-------------|
| `installation` | `uv sync` instructions |
| `architecture` | Directory tree of the project |
| `tech_stack` | Dependency table parsed from `pyproject.toml` |

Set `managed = []` to disable all automatic section management (docs pages use this).

## Loading

`load_config(root: Path) → MarkProofConfig` reads `root/markproof.toml` using Python's built-in `tomllib`. If the file does not exist, defaults are returned without error.

## Docs-Specific Config

The `docs/` directory contains its own `markproof.toml`:

```toml
[sections]
managed = []
```

This disables section checks when running `markproof check` against documentation pages — the check still validates all Python code blocks within those pages.

## Per-Block Metadata

In addition to the project-level config, individual code blocks can be annotated with HTML comments:

| Annotation | Effect |
|------------|--------|
| `<!-- markproof:skip -->` | Block is not executed |
| `<!-- markproof:expect_stdout=value -->` | Functional-test assertion: block stdout must equal `value` |
| `<!-- markproof:expect_error=ExcType -->` | Functional-test assertion: block must raise exception of type `ExcType` |

Multiple annotations can be combined in a single comment or across consecutive comments.
