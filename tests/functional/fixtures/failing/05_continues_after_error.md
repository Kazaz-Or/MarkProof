# Continues After Error

The executor never aborts on failure — all blocks are attempted regardless
of earlier errors. This fixture has a failing block followed by a passing
block to verify the "never abort" invariant.

```python
result = 1 / 0
```

```python
print("still_running")
```
