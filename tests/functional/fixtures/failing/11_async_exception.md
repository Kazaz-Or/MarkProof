# Async Exception

An uncaught exception raised inside an async coroutine awaited at top-level
propagates out of the executor and causes the block to fail.

```python
import asyncio

async def boom():
    raise ValueError("async failure")

await boom()
```
