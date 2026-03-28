# Second Block Uses Name From Failed Block

Block 1 fails before assigning `x`. Block 2 tries to use `x`, which was
never added to the namespace, so it raises NameError. Both blocks fail.

```python
x = 1 / 0
```

```python
print(x * 2)
```
