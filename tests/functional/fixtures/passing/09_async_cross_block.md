# Async Cross-Block

An async function defined in block 1 can be awaited at top-level in block 2.
The shared namespace carries the coroutine function across blocks.

```python
import asyncio

async def double(n: int) -> int:
    await asyncio.sleep(0)
    return n * 2
```

```python
result = await double(21)
print(result)
```
