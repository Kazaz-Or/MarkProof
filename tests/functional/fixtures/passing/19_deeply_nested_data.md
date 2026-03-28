# Deeply Nested Data

Complex data structures built across blocks remain intact in the shared
namespace. Mutations in later blocks are visible in even later blocks.

```python
data = {"users": [{"name": "alice", "score": 10}, {"name": "bob", "score": 20}]}
```

```python
data["users"].append({"name": "carol", "score": 30})
```

```python
total = sum(u["score"] for u in data["users"])
print(total)
```
