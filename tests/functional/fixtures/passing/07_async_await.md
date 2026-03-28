# Async Await

Top-level `await` is detected and the block is transparently wrapped in a
coroutine. After execution, non-private locals are promoted back into the
shared namespace.

<!-- markproof:expect_stdout=42 -->
```python
import asyncio

async def compute():
    await asyncio.sleep(0)
    return 42

result = await compute()
print(result)
```
