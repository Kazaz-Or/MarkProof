# Data Pipeline Tutorial

A worked example of a CSV-processing pipeline. Every code block here is validated
by MarkProof — if the pipeline logic breaks, the documentation fails.

Run the check yourself:

```bash
markproof check README.md --root .
```

---

## Setup

```python
import csv
import io
import statistics
from dataclasses import dataclass, field
```

---

## The data model

```python
@dataclass
class Sale:
    product: str
    quantity: int
    unit_price: float

    @property
    def total(self) -> float:
        return self.quantity * self.unit_price
```

---

## Loading records from CSV

We use an in-memory CSV here so the example is self-contained and has no external
file dependencies:

```python
RAW_CSV = """\
product,quantity,unit_price
Widget A,10,2.50
Widget B,3,15.00
Widget C,7,5.00
Widget A,5,2.50
"""

def load_sales(csv_text: str) -> list[Sale]:
    reader = csv.DictReader(io.StringIO(csv_text))
    return [
        Sale(
            product=row["product"],
            quantity=int(row["quantity"]),
            unit_price=float(row["unit_price"]),
        )
        for row in reader
    ]

sales = load_sales(RAW_CSV)
```

<!-- markproof:expect_stdout=4 -->
```python
print(len(sales))
```

---

## Aggregation

```python
def total_revenue(records: list[Sale]) -> float:
    return sum(s.total for s in records)

def revenue_by_product(records: list[Sale]) -> dict[str, float]:
    result: dict[str, float] = {}
    for s in records:
        result[s.product] = result.get(s.product, 0.0) + s.total
    return result

revenue = total_revenue(sales)
by_product = revenue_by_product(sales)
```

<!-- markproof:expect_stdout=117.5 -->
```python
print(revenue)
```

---

## Statistics

```python
totals = [s.total for s in sales]
mean_sale = statistics.mean(totals)
median_sale = statistics.median(totals)
```

```python
print(f"Mean sale  : ${mean_sale:.2f}")
print(f"Median sale: ${median_sale:.2f}")
```

---

## Async variant — fetching from an API

Real pipelines often pull data from remote sources. MarkProof handles top-level
`await` transparently — no boilerplate required:

<!-- markproof:skip -->
```python
# Skipped in CI: requires network access
import httpx

async with httpx.AsyncClient() as client:
    response = await client.get("https://api.example.com/sales")
    data = response.json()
```

---

## Error guard — invalid CSV

Document what happens with bad input so readers know what to expect:

<!-- markproof:expect_error=ValueError -->
```python
def load_sales_strict(csv_text: str) -> list[Sale]:
    records = load_sales(csv_text)
    if not records:
        raise ValueError("CSV contained no data rows")
    return records

load_sales_strict("")   # empty string → no rows → ValueError
```
