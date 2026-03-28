# Skip Annotated

A block annotated with `<!-- markproof:skip -->` is never executed, so it
cannot cause the suite to fail even if it contains invalid code.

<!-- markproof:skip -->
```python
raise RuntimeError("this should never run")
```

<!-- markproof:expect_stdout=done -->
```python
print("done")
```
