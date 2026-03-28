# Install Blocks Skipped

Shell blocks with package-manager commands are classified as INSTALL and
skipped automatically — they are never passed to `exec()`.

```bash
pip install markproof
```

```bash
uv add markproof
```

<!-- markproof:expect_stdout=1 -->
```python
print(1)
```
