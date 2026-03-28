# Simple Print

A single block that prints a value. The executor captures stdout and the
functional test asserts the expected output.

<!-- markproof:expect_stdout=hello -->
```python
print("hello")
```
