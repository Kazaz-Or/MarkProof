# Cumulative State

Variables defined in an earlier block are visible in later blocks because
all blocks share a single namespace per `execute()` call.

```python
x = 10
y = 20
```

<!-- markproof:expect_stdout=30 -->
```python
print(x + y)
```
