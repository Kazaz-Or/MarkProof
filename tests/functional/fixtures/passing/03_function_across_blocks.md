# Function Across Blocks

A function defined in one block can be called in a subsequent block.

```python
def add(a, b):
    return a + b
```

<!-- markproof:expect_stdout=5 -->
```python
print(add(2, 3))
```
