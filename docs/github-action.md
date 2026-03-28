# GitHub Action

MarkProof is available as a GitHub Action so you can validate your documentation
in any CI pipeline with a single `uses:` line — no Python setup required.

## Quick Start

Add this to any workflow:

```yaml
- uses: actions/checkout@v4

- name: Validate docs
  uses: Kazaz-Or/MarkProof@v1
  with:
    path: README.md
    root: .
```

By default the action regenerates managed sections first, then validates the file.
If the README contains a broken Python block or a missing managed section, the
step fails and the workflow exits 1.

## Inputs

| Input | Required | Default | Description |
|-------|----------|---------|-------------|
| `path` | No | `README.md` | Path to the Markdown file to validate, relative to the repo root |
| `root` | No | `.` | Project root for `markproof.toml` config lookup |
| `generate` | No | `true` | Regenerate managed sections before checking. Set to `false` to skip regeneration and only validate the existing file |
| `version` | No | latest | MarkProof version to install from PyPI (e.g. `1.2.3`). Omit to always use the latest release |

## Examples

### Validate README only (no regeneration)

Use this when the README is committed as-is and regeneration is not needed:

```yaml
- uses: Kazaz-Or/MarkProof@v1
  with:
    path: README.md
    root: .
    generate: 'false'
```

### Pin to a specific version

```yaml
- uses: Kazaz-Or/MarkProof@v1
  with:
    path: README.md
    root: .
    version: '1.2.3'
```

### Validate a docs library page

Each page in `docs/` has its own `markproof.toml` that disables section checks.
The action still validates all Python code blocks within the page:

```yaml
- uses: Kazaz-Or/MarkProof@v1
  with:
    path: docs/architecture.md
    root: docs/
    generate: 'false'
```

### Validate multiple files in a matrix

```yaml
jobs:
  docs:
    strategy:
      matrix:
        doc:
          - { path: README.md, root: . }
          - { path: docs/configuration.md, root: docs/ }
          - { path: docs/architecture.md, root: docs/ }
    steps:
      - uses: actions/checkout@v4
      - uses: Kazaz-Or/MarkProof@v1
        with:
          path: ${{ matrix.doc.path }}
          root: ${{ matrix.doc.root }}
          generate: 'false'
```

### Full generate-and-check workflow

Regenerate the README, commit the changes, and fail if anything is broken:

```yaml
jobs:
  docs:
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v4

      - name: Generate and validate README
        uses: Kazaz-Or/MarkProof@v1
        with:
          path: README.md
          root: .
          generate: 'true'

      - name: Commit regenerated README
        run: |
          git config user.name  "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add README.md
          git diff --cached --quiet || git commit -m "chore: regenerate README"
          git push
```

## How It Works

The action is a composite action — it runs directly on the runner without Docker.

1. Sets up [uv](https://docs.astral.sh/uv/) using `astral-sh/setup-uv`.
2. Installs MarkProof via `uvx` (no persistent installation, runs in an isolated environment).
3. Optionally runs `markproof generate` to update managed sections.
4. Runs `markproof check` to validate the file.

## Relationship to the CLI

The action is a thin wrapper around the same `markproof` CLI you run locally.
All behavior is identical — the action simply handles installation and invocation.

To replicate locally what the action does:

```bash
uvx markproof generate .
uvx markproof check README.md --root .
```

Or with the package installed:

```bash
markproof generate .
markproof check README.md --root .
```
