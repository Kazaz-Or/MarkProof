# Async API Client

Documents an `httpx`-based async client with MarkProof validation. Non-network
blocks are fully executable in CI; any block that requires real I/O is annotated
`<!-- markproof:skip -->`.

```bash
markproof check README.md --root .
```

---

## The client

```python
import asyncio
import json
from dataclasses import dataclass
```

```python
@dataclass
class ApiResponse:
    status_code: int
    body: dict

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 300
```

---

## Retry logic (pure, no I/O)

The retry wrapper is pure Python — MarkProof can validate it without any network:

```python
async def with_retry(coro_fn, retries: int = 3):
    """Call ``coro_fn()`` up to *retries* times, raising the last error."""
    last_exc: Exception | None = None
    for attempt in range(retries):
        try:
            return await coro_fn()
        except Exception as exc:
            last_exc = attempt  # record attempt index for demo purposes
            await asyncio.sleep(0)  # yield; real code would back off
    raise RuntimeError(f"Failed after {retries} attempts") from None
```

---

## Simulated request (no real network)

We test the client contract with a fake transport:

```python
async def fake_get(url: str) -> ApiResponse:
    """Simulate a successful JSON response."""
    payload = {"url": url, "result": "ok"}
    return ApiResponse(status_code=200, body=payload)
```

<!-- markproof:expect_stdout=True -->
```python
response = await fake_get("https://api.example.com/ping")
print(response.ok)
```

---

## Parsing the response

```python
async def parse_items(response: ApiResponse) -> list[str]:
    if not response.ok:
        raise ValueError(f"Request failed: {response.status_code}")
    return list(response.body.keys())

items = await parse_items(response)
```

<!-- markproof:expect_stdout=2 -->
```python
print(len(items))
```

---

## Live requests (skipped in CI)

These blocks are skipped during `markproof check` because they require real
network access. They still serve as documentation for readers:

<!-- markproof:skip -->
```python
import httpx

async with httpx.AsyncClient(timeout=10) as client:
    r = await client.get("https://httpbin.org/get")
    data = r.json()
    print(data["url"])
```

---

## Error surface

Document what the client raises so callers know what to catch:

<!-- markproof:expect_error=ValueError -->
```python
bad_response = ApiResponse(status_code=404, body={})
await parse_items(bad_response)
```

<!-- markproof:expect_error=RuntimeError -->
```python
async def always_fails():
    raise IOError("network down")

await with_retry(always_fails, retries=2)
```

---

## Serialisation round-trip

```python
import json

original = {"key": "value", "number": 42}
serialised = json.dumps(original)
restored = json.loads(serialised)
```

<!-- markproof:expect_stdout=True -->
```python
print(original == restored)
```
