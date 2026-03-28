# Async Exception Caught Internally

An exception raised inside an async coroutine and caught within the same
block does not propagate to the executor.

```python
import asyncio

async def safe_divide(a, b):
    if b == 0:
        raise ZeroDivisionError("cannot divide by zero")
    return a / b

try:
    result = await safe_divide(10, 0)
except ZeroDivisionError:
    result = 0

print(result)
```
