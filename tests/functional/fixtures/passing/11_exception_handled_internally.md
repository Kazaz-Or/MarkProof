# Exception Handled Internally

An exception raised and caught inside a single block does not propagate to
the executor. Only uncaught exceptions become block errors.

```python
try:
    result = 1 / 0
except ZeroDivisionError:
    result = -1

print(result)
```
