# Getting Started with MarkProof

This example shows how MarkProof validates every Python code block in a Markdown
file. Drop this file into any project and run:

```bash
markproof check README.md --root .
```

---

## Why documentation lies

READMEs go stale. A function gets renamed, a dependency is upgraded, and suddenly
the "quick start" raises an `ImportError`. MarkProof treats docs as tests — if a
block fails, the build fails.

---

## Your first validated block

The simplest use case: a code block that must not raise.

```python
message = "Hello from MarkProof!"
print(message)
```

MarkProof runs that block and, if it raises anything, reports a failure. No special
annotation needed — every Python block is checked by default.

---

## Assertions with `expect_stdout`

Pin the expected output so MarkProof catches silent regressions:

<!-- markproof:expect_stdout=6 -->
```python
def add(a, b):
    return a + b

print(add(2, 4))
```

If `add` were accidentally changed to multiply, the captured stdout (`8`) would not
match the annotation (`6`) and the check would fail.

---

## Cumulative state across blocks

All blocks in a single file share one namespace — just like a Jupyter notebook.
Imports and variables defined above are available below.

```python
import math

PI = math.pi
```

```python
# PI is still in scope from the block above
circumference = 2 * PI * 5
print(f"Circumference of r=5 circle: {circumference:.4f}")
```

---

## Skipping blocks that can't run in CI

Installation commands, environment-specific snippets, or intentional error
demonstrations can be excluded with `<!-- markproof:skip -->`:

<!-- markproof:skip -->
```python
# This block is never executed
import some_package_not_installed_in_ci
```

MarkProof records it as skipped and moves on.

---

## Documenting expected errors

Use `expect_error` to assert that a block raises a specific exception. This is
useful for teaching defensive programming or documenting invalid-input behaviour:

<!-- markproof:expect_error=ValueError -->
```python
int("not a number")
```

The check passes because `int("not a number")` raises `ValueError`, matching the
annotation. Any other exception type — or no exception — would be a failure.

---

## What happens when a block fails?

MarkProof **never aborts early**. Every block in the file is attempted, and a
complete failure report is printed at the end. This means one broken example
doesn't hide other problems further down in the document.

```bash
markproof check README.md --root .
# exit 1 with a table listing every block error
```
