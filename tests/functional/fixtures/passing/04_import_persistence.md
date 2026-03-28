# Import Persistence

An import in block 1 remains available in block 2 because the namespace is
shared for the entire document.

```python
import math
```

<!-- markproof:expect_stdout=3 -->
```python
print(int(math.pi))
```
