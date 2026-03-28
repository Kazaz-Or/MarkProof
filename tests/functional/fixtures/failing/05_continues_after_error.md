# Continues After Error

The executor never aborts on failure — all blocks are attempted regardless
of earlier errors. This fixture has a failing block followed by a passing
block to verify the "never abort" invariant.

<!-- markproof:expect_error=ZeroDivisionError -->
```python
result = 1 / 0
```

<!-- markproof:expect_stdout=still_running -->
```python
print("still_running")
```
