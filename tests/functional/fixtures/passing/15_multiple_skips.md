# Multiple Skip Annotations

Multiple blocks can be individually annotated with `<!-- markproof:skip -->`.
Each annotation applies only to the immediately following block.

<!-- markproof:skip -->
```python
raise RuntimeError("block one should be skipped")
```

<!-- markproof:skip -->
```python
raise ValueError("block two should also be skipped")
```

```python
print("only this runs")
```
