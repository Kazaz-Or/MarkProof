# Metadata Cleared By Prose

A `<!-- markproof:skip -->` comment is cleared if any non-blank prose line
appears between the comment and the code block. The block is executed normally.

<!-- markproof:skip -->
This prose line clears the skip annotation above.

```python
print("executed normally")
```
