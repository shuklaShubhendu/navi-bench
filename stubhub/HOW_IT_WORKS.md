# StubHub Verifier - Technical Documentation

## Overview

The StubHub Verifier is a production-level browser automation testing system that verifies AI agent navigation behavior on StubHub. It features multi-tab tracking, real-time navigation monitoring, and comprehensive data extraction using LD+JSON structured data.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    StubHub Website (stubhub.com)                │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│              JavaScript DOM Scraper (~1,400 lines)              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │  LD+JSON    │  │    URL      │  │    DOM      │             │
│  │ Extraction  │  │   Parser    │  │  Scraping   │             │
│  │  (Tier 1)   │  │  (Tier 2)   │  │  (Tier 3)   │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
│                                                                 │
│  Returns: 50+ fields including event, performer, venue, price  │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│              Python Verifier Engine (~800 lines)                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │   Query     │  │  Coverage   │  │   Score     │             │
│  │  Matching   │  │  Tracking   │  │ Calculation │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│     Result: {score: 1.0, n_covered: 1, is_query_covered: [T]}   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3-Tier Data Extraction

The system uses a prioritized extraction strategy:

| Tier | Source | Reliability | When Used |
|------|--------|-------------|-----------|
| **1** | LD+JSON (Schema.org) | Highest | Category/grouping pages |
| **2** | URL Parameters | High | Event pages with filters |
| **3** | DOM Scraping | Medium | Fallback for all pages |

### Tier 1: LD+JSON Extraction (Primary)

StubHub embeds Schema.org structured data on category pages:

```javascript
const getEventsFromLdJson = () => {
    const scripts = document.querySelectorAll('script[type="application/ld+json"]');
    // Parses: SportsEvent, MusicEvent, TheaterEvent
    // Extracts: performer, venue, dates, prices, status
};
```

**Fields from LD+JSON:**
- `eventName`, `eventType`, `description`
- `performer`, `performerType` (SportsTeam, MusicGroup)
- `venue`, `streetAddress`, `city`, `state`, `postalCode`, `country`
- `startTime`, `doorTime`, `endDate`
- `lowPrice`, `highPrice`, `currency`
- `eventStatus` (EventScheduled, EventRescheduled, EventCancelled)
- `breadcrumbs` (navigation hierarchy)

### Tier 2: URL Parameter Extraction

```javascript
const parseUrlFilters = () => {
    const url = new URL(window.location.href);
    return {
        urlSections: url.searchParams.get('sections')?.split(','),
        urlQuantity: parseInt(url.searchParams.get('quantity')),
        urlMinPrice: parseFloat(url.searchParams.get('minPrice')),
        urlMaxPrice: parseFloat(url.searchParams.get('maxPrice')),
        urlSort: url.searchParams.get('sort'),
    };
};
```

### Tier 3: DOM Scraping (Fallback)

```javascript
const scrapeDOM = () => {
    return {
        eventName: document.querySelector('h1')?.textContent,
        price: parsePrice(document.querySelector('[data-testid="price"]')?.textContent),
        venue: document.querySelector('[data-testid="venue"]')?.textContent,
        // ... 30+ more fields
    };
};
```

---

## Multi-Tab Navigation Tracking

The system tracks navigation across all browser tabs in real-time:

```python
class NavigationTracker:
    """Tracks navigation events across all pages."""
    
    async def attach_to_page(self, page: Page) -> None:
        """Attach tracking to a page."""
        async def on_navigate(frame):
            if frame != page.main_frame:
                return
            self.navigation_count += 1
            await self.evaluator.update(page=page)
        
        page.on("framenavigated", lambda f: asyncio.create_task(on_navigate(f)))
    
    async def handle_new_page(self, new_page: Page) -> None:
        """Handle new tab/popup windows."""
        await new_page.wait_for_load_state("domcontentloaded")
        await self.attach_to_page(new_page)
        await self.evaluator.update(page=new_page)
    
    def attach_to_context(self, context: BrowserContext) -> None:
        """Attach to browser context for new page detection."""
        context.on("page", lambda p: asyncio.create_task(self.handle_new_page(p)))
```

**Key Features:**
- Real-time updates on every navigation via `framenavigated` event
- Automatic detection and tracking of new tabs/popups
- Thread-safe with asyncio lock
- Verbose logging of all navigation events

---

## Demo Suite

### Available Demos

| Demo | File | Description |
|------|------|-------------|
| **Interactive** | `demo_stubhub.py` | Menu-based scenario selection |
| **Automated** | `auto_demo_stubhub.py` | Fully automated browser navigation |
| **Batch** | `batch_demo_stubhub.py` | Multiple scenario testing with JSON export |

### Running the Demos

```bash
# Interactive menu with scenario selection
python demo_stubhub.py

# Fully automated (no human interaction)
python auto_demo_stubhub.py

# Batch testing with export
python batch_demo_stubhub.py --count 5 --export

# Headless batch for CI/CD
python batch_demo_stubhub.py --headless --export -o results.json
```

### Expected Output

```
================================================================================
STUBHUB TICKET VERIFICATION SYSTEM
================================================================================

Available scenarios:

  [1] NBA Game Ticket Verification
      Verify NBA basketball game ticket availability

  [2] Concert Ticket Verification
      Verify concert ticket availability

  [3] Theater Show Verification
      Verify Broadway/theater ticket availability

  [A] Run all scenarios
  [Q] Quit

Select scenario (1-3, A, or Q): 1

================================================================================
STUBHUB VERIFICATION: NBA Game Ticket Verification
================================================================================
Task ID:     stubhub/sports/nba/001
Category:    sports
Location:    United States
Timezone:    America/New_York
--------------------------------------------------------------------------------
TASK: Search for any NBA basketball game tickets...
================================================================================

Press ENTER to launch browser...
```

---

## Query Matching System

### Multi-Candidate Query Structure

```python
query = {
    # Event identifiers (OR matching)
    "event_names": ["nba", "basketball"],
    
    # Category filters
    "event_categories": ["sports"],
    
    # Location filters
    "cities": ["los angeles", "new york"],
    "venues": ["crypto.com arena", "msg"],
    
    # Date/time filters
    "dates": ["2025-12-20", "2025-12-21"],
    
    # Price constraints
    "min_price": 50.0,
    "max_price": 500.0,
    
    # Availability
    "require_available": False,  # Credit even if sold out
}
```

### Matching Algorithm

```
For each scraped event:
  1. ✓ Event name matches ANY of event_names (substring, case-insensitive)
  2. ✓ Category matches ANY of event_categories
  3. ✓ City matches ANY of cities (if specified)
  4. ✓ Venue matches ANY of venues (if specified)
  5. ✓ Date matches ANY of dates (if specified)
  6. ✓ Price ≤ max_price AND ≥ min_price
  7. ✓ Availability matches require_available

Score = n_covered_queries / total_queries
```

---

## Complete Data Flow

```
┌──────────────────┐
│   User/Agent     │
│  navigates to    │
│   StubHub.com    │
└────────┬─────────┘
         │ (clicks, searches, navigates)
         ▼
┌──────────────────┐
│  NavigationTracker │◄──── page.on("framenavigated")
│  (Real-time)      │      context.on("page") for new tabs
└────────┬─────────┘
         │ (triggers on every navigation)
         ▼
┌──────────────────┐
│   JS Scraper     │◄──── page.evaluate(scraper.js)
│  (In Browser)    │
│                  │
│  Extraction:     │
│  1. LD+JSON      │ ← Primary (Schema.org)
│  2. URL Params   │ ← Secondary
│  3. DOM          │ ← Fallback
│                  │
│  Returns 50+     │
│  fields          │
└────────┬─────────┘
         │ (JSON data)
         ▼
┌──────────────────┐
│  Python Verifier │◄──── evaluator.update(page)
│                  │
│  Query matching: │
│  - event_names   │
│  - categories    │
│  - cities        │
│  - price range   │
│  - availability  │
│  - URL params    │
└────────┬─────────┘
         │ (computes coverage)
         ▼
┌──────────────────┐
│  Result Object   │◄──── evaluator.compute()
│                  │
│  score: 1.0      │  (100% = all matched)
│  n_covered: 1    │
│  n_queries: 1    │
│  pages_navigated │
└──────────────────┘
```

---

## Stealth Browser Configuration

The system uses anti-detection techniques:

```python
class BrowserManager:
    async def launch(self, playwright) -> tuple:
        browser = await playwright.chromium.launch(
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
                "--no-sandbox",
            ],
        )
        
        context = await browser.new_context(
            viewport={"width": 1366, "height": 768},
            user_agent="Mozilla/5.0 ...",
            locale="en-US",
        )
        
        # Anti-detection scripts
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            window.chrome = { runtime: {} };
        """)
        
        return browser, context, await context.new_page()
```

---

## Files Summary

| File | Purpose | Lines |
|------|---------|-------|
| `stubhub_info_gathering.js` | JavaScript DOM scraper | ~1,400 |
| `stubhub_info_gathering.py` | Python verifier engine | ~800 |
| `demo_stubhub.py` | Interactive demo (menu) | ~500 |
| `auto_demo_stubhub.py` | Automated browser agent | ~280 |
| `batch_demo_stubhub.py` | Batch testing runner | ~380 |
| `test_stubhub_unit.py` | Unit tests (20 tests) | ~330 |
| `stubhub_complete_features.csv` | Feature inventory | 83 features |
| `fnal_doc.md` | Complete documentation | ~600 |

**Total: ~4,300 lines of code**

---

## Key Design Decisions

1. **3-Tier Extraction**: LD+JSON → URL → DOM for maximum reliability
2. **Multi-Tab Tracking**: Real-time navigation monitoring across all tabs
3. **Schema.org Integration**: Uses StubHub's own structured data
4. **No Hardcoded Data**: All team/artist names from dynamic extraction
5. **Production Demos**: Interactive, automated, and batch modes
6. **CI/CD Ready**: JSON export, headless mode, exit codes
7. **83 Features**: Comprehensive coverage for all StubHub functionality

---

**End of Document**
