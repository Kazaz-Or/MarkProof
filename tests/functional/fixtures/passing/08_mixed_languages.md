# Mixed Languages

Non-Python blocks (bash, javascript, etc.) are skipped automatically.
Only blocks with a Python language tag are executed.

```bash
echo "setup done"
```

```javascript
console.log("js ignored");
```

<!-- markproof:expect_stdout=running -->
```python
print("running")
```
