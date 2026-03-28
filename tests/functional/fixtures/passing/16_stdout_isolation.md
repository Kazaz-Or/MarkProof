# Stdout Isolation

Each block's stdout is captured independently. Output from one block does
not bleed into another. Skipped blocks produce no stdout at all.

```python
print("block one")
```

```bash
echo "this is bash and gets skipped"
```

```python
print("block three")
```
