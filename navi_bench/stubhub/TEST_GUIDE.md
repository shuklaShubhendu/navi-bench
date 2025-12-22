# StubHub Verifier - Test Guide

## Manual Testing Steps

### 1. Test JavaScript Scraper

Open browser console on StubHub pages and run:

```javascript
// Copy the entire content of stubhub_info_gathering.js
// Paste in console and run
const results = (() => {
    // ... scraper code ...
})();

console.log(results);
```

### 2. Expected Output

#### Search Page
```javascript
[
  {
    url: "https://www.stubhub.com/...",
    eventName: "Los Angeles Lakers at LA Clippers",
    date: "2025-12-20",
    time: "19:30:00",
    venue: "Intuit Dome",
    price: 150.00,
    info: "search_result"
  }
]
```

#### Event Detail Page
```javascript
[
  {
    url: "https://www.stubhub.com/event/...",
    eventName: "Los Angeles Lakers at LA Clippers",
    date: "2025-12-20",
    time: "19:30:00",
    venue: "Intuit Dome",
    section: "T32",
    price: 150.00,
    ticketCount: 2,
    info: "available"
  }
]
```

### 3. Test Python Verifier

```python
import asyncio
from playwright.async_api import async_playwright
from navi_bench.stubhub import StubHubInfoGathering

async def test_verifier():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        
        # Create verifier
        verifier = StubHubInfoGathering(queries=[[{
            "event_names": ["lakers"],
            "dates": ["2025-12-20"],
            "cities": ["los angeles", "inglewood"]
        }]])
        
        # Navigate to StubHub
        await page.goto("https://www.stubhub.com/la-clippers-inglewood-tickets-12-20-2025/event/159098161/")
        
        # Update with page data
        await verifier.update(page=page)
        
        # Compute result
        result = await verifier.compute()
        
        print(f"Score: {result.score}")
        print(f"Queries covered: {result.n_covered}/{result.n_queries}")
        
        await browser.close()

asyncio.run(test_verifier())
```

### 4. Test Dataset Item

```python
import json
from navi_bench.base import DatasetItem, instantiate

dataset_row = {
    "task_id": "navi_bench/stubhub/lakers/0",
    "task_generation_config_json": json.dumps({
        "_target_": "navi_bench.stubhub.stubhub_info_gathering.generate_task_config_deterministic",
        "mode": "any",
        "url": "https://www.stubhub.com",
        "task": "Find Lakers tickets in Los Angeles for December 20, 2025 under $500",
        "queries": [[{
            "event_names": ["lakers", "los angeles lakers"],
            "dates": ["2025-12-20"],
            "cities": ["los angeles", "inglewood"],
            "max_price": 500.00
        }]],
        "location": "Los Angeles, CA, United States",
        "timezone": "America/Los_Angeles",
    }),
    "env": "real",
    "domain": "stubhub",
    "l1_category": "entertainment",
    "l2_category": "sports",
}

dataset_item = DatasetItem.model_validate(dataset_row)
task_config = dataset_item.generate_task_config()
evaluator = instantiate(task_config.eval_config)

print("Task:", task_config.task)
print("Evaluator:", evaluator)
```

## Common Issues & Fixes

### Issue 1: Scraper returns empty array
**Cause:** DOM selectors don't match actual page structure  
**Fix:** Update selectors in `stubhub_info_gathering.js`

### Issue 2: Date parsing fails
**Cause:** Date format different than expected  
**Fix:** Update `parseDateTime()` function

### Issue 3: Price not extracted
**Cause:** Price format includes currency symbol  
**Fix:** Update `parsePrice()` regex

### Issue 4: Event name mismatch
**Cause:** Case sensitivity or extra whitespace  
**Fix:** Use `.lower()` and `.strip()` in matching

## Validation Checklist

- [ ] Scraper extracts event name correctly
- [ ] Date parsed in YYYY-MM-DD format
- [ ] Time parsed in HH:MM:SS format
- [ ] Venue name extracted
- [ ] Price extracted as float
- [ ] Ticket count extracted
- [ ] Section extracted
- [ ] Availability status correct
- [ ] Python verifier matches correctly
- [ ] Score calculation works
- [ ] Multiple queries supported

## Performance Targets

- Scraper execution: <100ms
- Page load + scrape: <2s
- Verifier matching: <10ms
- End-to-end: <3s

## Next Steps

1. Run manual tests on real pages
2. Fix any selector issues
3. Add more event types (concerts, theater)
4. Create test dataset
5. Benchmark performance
