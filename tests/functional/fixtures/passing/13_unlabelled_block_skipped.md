# Unlabelled Block Skipped

A fenced block with no language tag is not treated as Python and is skipped
by the executor. It cannot cause a failure.

```
this is not Python
raise RuntimeError("should not run")
```

```python
print("ok")
```
