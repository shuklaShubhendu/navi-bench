# StubHub Info Gathering Verifier

## Overview

JavaScript-based verifier for www.stubhub.com that validates AI agent ticket search results. Follows the OpenTable pattern for event ticket verification.

---

## 📁 Files

- `stubhub_info_gathering.js` - JavaScript scraper (350+ lines)
- `stubhub_info_gathering.py` - Python verifier (400+ lines)
- `__init__.py` - Module exports

---

## 🎯 Features

### JavaScript Scraper
Extracts event information from StubHub pages:
- Event names
- Dates and times
- Venues and locations
- Ticket prices
- Seat sections
- Availability status

### Python Verifier
Matches scraped data against expected queries:
- Multi-candidate query support
- Flexible matching (event names, dates, venues, etc.)
- Coverage tracking
- Exhaustive search detection

---

## 🚀 Usage

### Basic Example

```python
from navi_bench.stubhub import generate_task_config_deterministic
from navi_bench.base import instantiate

# Create task configuration
task_config = generate_task_config_deterministic(
    mode="any",
    task="Search for Lakers tickets in Los Angeles for December 20, 2025",
    queries=[[{
        "event_names": ["lakers", "los angeles lakers"],
        "dates": ["2025-12-20"],
        "cities": ["los angeles", "inglewood"],
        "max_price": 500.00
    }]],
    location="Los Angeles, CA, United States",
    timezone="America/Los_Angeles",
)

# Instantiate evaluator
evaluator = instantiate(task_config.eval_config)

# Use with Playwright page
await evaluator.update(page=page)
result = await evaluator.compute()

print(f"Score: {result.score}")  # 1.0 if query covered
```

---

## 📊 Query Structure

### MultiCandidateQuery

```python
{
    "event_names": ["lakers vs warriors", "warriors vs lakers"],
    "dates": ["2025-01-15", "2025-01-16"],
    "times": ["19:30:00", "20:00:00"],
    "venues": ["crypto.com arena"],
    "cities": ["los angeles"],
    "min_tickets": 2,
    "max_price": 500.00
}
```

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `event_names` | list[str] | Acceptable event names (case-insensitive) |
| `dates` | list[str] | Acceptable dates (YYYY-MM-DD format) |
| `times` | list[str] | Acceptable times (HH:MM:SS format) |
| `venues` | list[str] | Acceptable venue names |
| `cities` | list[str] | Acceptable cities |
| `min_tickets` | int | Minimum number of tickets required |
| `max_price` | float | Maximum price per ticket |

---

## 🔍 How It Works

### 1. JavaScript Scraping

The scraper runs on StubHub pages and extracts:

```javascript
{
    url: "https://www.stubhub.com/...",
    eventName: "Los Angeles Lakers at LA Clippers",
    date: "2025-12-20",
    time: "19:30:00",
    venue: "Intuit Dome",
    city: "Inglewood",
    section: "T32",
    price: 150.00,
    ticketCount: 2,
    info: "available"
}
```

### 2. Python Matching

The verifier checks if scraped data matches queries:

```python
# Check event name
if info["eventName"].lower() in query["event_names"]:
    # Check date
    if info["date"] in query["dates"]:
        # Check price
        if info["price"] <= query["max_price"]:
            # MATCH!
            return True
```

### 3. Coverage Calculation

```python
score = n_covered / n_queries
```

---

## 📋 Supported Page Types

1. **Search Results** - `/search?q=...` or `/s?...`
2. **Event Detail** - `/event/...`
3. **Ticket Selection** - `/checkout` or `/tickets/...`

---

## ⚙️ Task Generation

### Random Tasks

```python
from navi_bench.stubhub import generate_task_config_random

config = generate_task_config_random(
    event_type="sports",  # or "concert", "theater"
    city="Los Angeles",
    seed=42
)
```

### Deterministic Tasks

```python
from navi_bench.stubhub import generate_task_config_deterministic

config = generate_task_config_deterministic(
    mode="any",  # or "all"
    task="Find Lakers tickets...",
    queries=[[{...}]],
    location="Los Angeles, CA, United States",
    timezone="America/Los_Angeles"
)
```

---

## 🧪 Testing

```python
# Run the example
python navi_bench/stubhub/stubhub_info_gathering.py
```

---

## 📝 Notes

- StubHub uses dynamic JavaScript content
- Scraper handles lazy loading and infinite scroll
- Case-insensitive matching for event names and venues
- Flexible date/time matching
- Price filtering support

---

## 🔗 Related

- Based on [OpenTable verifier](../opentable/)
- Follows navi-bench framework patterns
- Uses Playwright for browser automation

---

## 📄 License

Apache 2.0
