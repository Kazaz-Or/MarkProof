# Parser

`parser.py` extracts fenced code blocks and `<!-- markproof:… -->` metadata from Markdown text.

## Public API

### `parse_text(text, path) → ParseResult`

Parses raw Markdown content and returns a `ParseResult` containing all discovered `CodeBlock` objects.

| Parameter | Type | Description |
|-----------|------|-------------|
| `text` | `str` | Raw Markdown content |
| `path` | `Path` | Logical document path (stored on result; not read here) |

### `parse_file(path) → ParseResult`

Convenience wrapper: reads `path` as UTF-8 text and calls `parse_text`.

## Fenced Code Block Detection

Opening fences match:

```
^(?P<fence>`{3,}|~{3,})(?P<lang>\w*)\s*$
```

Rules:
- The fence character must be `` ` `` or `~`.
- The opening fence must be 3 or more characters.
- The closing fence must use the **same character** and be **at least as long** as the opening fence.
- An unclosed block (EOF reached without closing fence) is treated as implicitly closed.

## Metadata Comments

Comments placed **before** a code block annotate that block:

```
<!-- markproof:key=value flag another=1 -->
```python
…
```

Parsing rules:
- `key=value` → stored as `{"key": "value"}`
- Bare `flag` → stored as `{"flag": "true"}`
- Blank lines between a comment and its block are **ignored** — the metadata still binds.
- Any **non-blank, non-comment** line between a comment and the next fence **clears** the pending metadata.
- Multiple comments accumulate: the most recently seen keys win.

## INSTALL vs USAGE Classification

A block is classified as `INSTALL` if its source matches any of these patterns (case-insensitive, multiline):

| Pattern | Examples |
|---------|---------|
| `pip install` / `pip3 install` | `pip install requests` |
| `uv add` | `uv add httpx` |
| `uv pip install` | `uv pip install ruff` |
| `conda install` | `conda install numpy` |
| `poetry add` | `poetry add pydantic` |
| `pipenv install` | `pipenv install flask` |

All other blocks are classified as `USAGE`.

## Data Models

```
ParseResult
  └─ path: Path
  └─ blocks: list[CodeBlock]
        ├─ source: str          # raw content between fences
        ├─ language: str        # lowercased lang tag ("python", "bash", …)
        ├─ line_number: int     # 1-based line of the opening fence
        ├─ kind: CodeBlockKind  # INSTALL | USAGE
        └─ metadata: dict[str, str]
```
