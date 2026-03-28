# Class Across Blocks

A class defined in one block can be instantiated and used in a subsequent
block via the shared cumulative namespace.

```python
class Counter:
    def __init__(self):
        self.value = 0

    def increment(self):
        self.value += 1
        return self.value
```

```python
c = Counter()
c.increment()
c.increment()
print(c.increment())
```
