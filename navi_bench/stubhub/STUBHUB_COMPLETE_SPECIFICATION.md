# StubHub Verifier - Complete Technical Specification

## Executive Summary

This document outlines the complete implementation plan for a JavaScript-based verifier for **www.stubhub.com**. The verifier will validate AI agent ticket search results by gathering event information through DOM scraping and matching against expected queries.

**Implementation Reference:** Based on the proven [OpenTable verifier pattern](https://github.com/yutori-ai/navi-bench/tree/main/navi_bench/opentable)

---

## Table of Contents

1. [Overview](#1-overview)
2. [Architecture](#2-architecture)
3. [Edge Cases Covered](#3-edge-cases-covered)
4. [JavaScript Scraper Specification](#4-javascript-scraper-specification)
5. [Python Verifier Specification](#5-python-verifier-specification)
6. [Query Structure](#6-query-structure)
7. [Task Generation](#7-task-generation)
8. [Supported Event Categories](#8-supported-event-categories)
9. [Venue Mappings](#9-venue-mappings)
10. [Testing Strategy](#10-testing-strategy)
11. [Deliverables](#11-deliverables)
12. [Timeline](#12-timeline)

---

## 1. Overview

### 1.1 Purpose
Build a verification system that can:
- Scrape event ticket information from StubHub pages
- Validate AI agent search results against expected criteria
- Calculate coverage scores for query matching
- Support multiple event types (sports, concerts, theater)

### 1.2 Key Features
- **JavaScript-based scraping** for dynamic content
- **Flexible query matching** with multiple alternatives
- **Comprehensive coverage calculation**
- **Support for all StubHub page types**
- **Edge case handling** for real-world scenarios

### 1.3 Technical Stack
- **Frontend:** JavaScript (browser-side scraping)
- **Backend:** Python (verification logic)
- **Framework:** Playwright (browser automation)
- **Testing:** Pytest + Manual validation

---

## 2. Architecture

### 2.1 Component Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    StubHub Verifier                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────┐    ┌──────────────────────────────┐  │
│  │  JavaScript      │    │  Python Verifier              │  │
│  │  Scraper         │───▶│  (stubhub_info_gathering.py)  │  │
│  │  (.js)           │    │                               │  │
│  └──────────────────┘    └──────────────────────────────┘  │
│          │                           │                       │
│          ▼                           ▼                       │
│  ┌──────────────────┐    ┌──────────────────────────────┐  │
│  │  DOM Parsing     │    │  Query Matching              │  │
│  │  - Event name    │    │  - Multi-candidate support   │  │
│  │  - Date/time     │    │  - Alternative conditions    │  │
│  │  - Venue         │    │  - Coverage calculation      │  │
│  │  - Price         │    │  - Exhaustive search         │  │
│  │  - Tickets       │    │                               │  │
│  └──────────────────┘    └──────────────────────────────┘  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Data Flow

```
1. Agent navigates to StubHub page
2. JavaScript scraper extracts data from DOM
3. Data passed to Python verifier
4. Verifier matches against expected queries
5. Coverage score calculated and returned
```

---

## 3. Edge Cases Covered

### 3.1 URL & Navigation Edge Cases

| # | Edge Case | Handling | Expected Behavior |
|---|-----------|----------|-------------------|
| 1 | Direct event URL | Parse event ID from path | Extract event details |
| 2 | Search results URL | Parse search query params | List matching events |
| 3 | Category browse URL | Parse category from path | List category events |
| 4 | Filter URL with params | Parse filter parameters | Apply filters to results |
| 5 | Paginated results | Handle page parameter | Aggregate all pages |
| 6 | URL with tracking params | Ignore utm_*, ref, etc. | Focus on event data |
| 7 | Mobile vs desktop URL | Normalize to standard | Same data extraction |
| 8 | Redirected URLs | Follow redirects | Extract final page data |
| 9 | URL encoding | Decode %20, %2B, etc. | Proper string handling |
| 10 | Case sensitivity | Lowercase normalization | case-insensitive matching |

### 3.2 Event Name Edge Cases

| # | Edge Case | Example | Handling |
|---|-----------|---------|----------|
| 11 | Team vs team format | "Lakers vs Warriors" | Match either order |
| 12 | Team at team format | "Lakers at Clippers" | Match home/away |
| 13 | Abbreviations | "LA Lakers" vs "Los Angeles Lakers" | Match both |
| 14 | Partial names | "Lakers" vs "Los Angeles Lakers" | Substring match |
| 15 | Special characters | "Guns N' Roses" | Handle apostrophes |
| 16 | Unicode characters | "Beyoncé" | UTF-8 support |
| 17 | Multiple performers | "Taylor Swift with Sabrina Carpenter" | Match primary |
| 18 | Tour names | "Eras Tour" | Match tour or artist |
| 19 | Event subtitles | "Game 1 - Western Conference Finals" | Parse main event |
| 20 | Cancelled/rescheduled | "[CANCELLED]" prefix | Detect status |

### 3.3 Date & Time Edge Cases

| # | Edge Case | Format | Handling |
|---|-----------|--------|----------|
| 21 | Standard date | "Dec 20, 2025" | Parse to YYYY-MM-DD |
| 22 | Full date | "December 20, 2025" | Parse month name |
| 23 | Short date | "12/20/25" | Parse numeric |
| 24 | ISO format | "2025-12-20" | Direct use |
| 25 | Relative date | "Tomorrow" | Calculate from today |
| 26 | Day of week | "Saturday" | Find next occurrence |
| 27 | Time zones | "7:30 PM PST" | Normalize to local |
| 28 | 12-hour format | "7:30 PM" | Convert to 24-hour |
| 29 | 24-hour format | "19:30" | Direct use |
| 30 | TBD/TBA times | "Time TBD" | Handle gracefully |
| 31 | Multi-day events | "Dec 20-22" | Parse date range |
| 32 | Year rollover | "Dec 31 - Jan 2" | Handle year change |

### 3.4 Venue & Location Edge Cases

| # | Edge Case | Example | Handling |
|---|-----------|---------|----------|
| 33 | Full venue name | "Crypto.com Arena" | Exact match |
| 34 | Venue aliases | "Staples Center" (old name) | Match both names |
| 35 | City variations | "Los Angeles" vs "LA" | Match abbreviations |
| 36 | State inclusion | "Inglewood, CA" | Parse city and state |
| 37 | Venue + city | "Chase Center, San Francisco" | Split and match |
| 38 | International venues | "O2 Arena, London" | Support global |
| 39 | Multiple venues | Same event different locations | Match any |
| 40 | Venue sections | "Section 101, Row A" | Parse seat details |

### 3.5 Price Edge Cases

| # | Edge Case | Example | Handling |
|---|-----------|---------|----------|
| 41 | Currency symbol | "$150" | Strip symbol, parse number |
| 42 | With fees | "$150 incl. fees" | Parse base or total |
| 43 | Price range | "$150 - $500" | Extract min/max |
| 44 | "From" pricing | "From $99" | Extract minimum |
| 45 | International currency | "€120", "£100" | Currency conversion |
| 46 | Indian Rupees | "INR 15,157" | Parse locale format |
| 47 | Thousands separator | "1,500" | Handle commas |
| 48 | No price available | "See tickets" | Return null |
| 49 | Price per ticket | "$50/ticket" | Parse unit price |
| 50 | Bundle pricing | "2 for $100" | Calculate per-ticket |

### 3.6 Ticket Availability Edge Cases

| # | Edge Case | Status | Handling |
|---|-----------|--------|----------|
| 51 | Available | "292 listings" | Mark available |
| 52 | Sold out | "Sold Out" | Mark unavailable |
| 53 | Limited | "Only 5 left!" | Mark limited |
| 54 | Waitlist | "Join Waitlist" | Mark waitlist |
| 55 | Presale | "Presale Tickets" | Mark presale |
| 56 | Resale only | "Resale tickets only" | Mark resale |
| 57 | Future sale | "On Sale Dec 1" | Mark future |
| 58 | Multiple listings | "50 listings" | Count available |
| 59 | Single ticket | "1 ticket left" | Parse quantity |
| 60 | Ticket types | "General Admission", "VIP" | Categorize |

### 3.7 Page Structure Edge Cases

| # | Edge Case | Page Type | Handling |
|---|-----------|-----------|----------|
| 61 | Search results page | /search?q=... | Extract all results |
| 62 | Event detail page | /event/12345 | Extract event info |
| 63 | Ticket listing page | /tickets/... | Extract listings |
| 64 | Category page | /sports/nba | Browse results |
| 65 | Venue page | /venue/msg | Venue events |
| 66 | Artist page | /artist/taylor-swift | Artist events |
| 67 | Homepage | / | Featured events |
| 68 | Error page | 404 | Handle gracefully |
| 69 | Loading state | Skeleton UI | Wait for content |
| 70 | Popup/modal | Cookie consent, etc. | Dismiss or ignore |

### 3.8 Dynamic Content Edge Cases

| # | Edge Case | Scenario | Handling |
|---|-----------|----------|----------|
| 71 | Lazy loading | Content loads on scroll | Wait for elements |
| 72 | Infinite scroll | More results on scroll | Capture visible |
| 73 | AJAX updates | Price updates | Re-scrape on change |
| 74 | Real-time updates | Availability changes | Handle current state |
| 75 | Hidden elements | display:none | Skip hidden |
| 76 | Viewport visibility | Off-screen content | Check visibility |
| 77 | Animation delays | Fade-in content | Wait for stable |
| 78 | Skeleton loaders | Placeholder content | Wait for real data |
| 79 | Error states | "Failed to load" | Detect and report |
| 80 | Empty results | "No events found" | Handle empty state |

### 3.9 Query Matching Edge Cases

| # | Edge Case | Scenario | Handling |
|---|-----------|----------|----------|
| 81 | Exact match | Query = Result | Score 1.0 |
| 82 | Partial match | Subset matches | Score partial |
| 83 | No match | Nothing matches | Score 0.0 |
| 84 | Multiple alternatives | Any of A, B, C | OR logic |
| 85 | All required | A AND B AND C | AND logic |
| 86 | Price under limit | price <= max_price | Filter check |
| 87 | Min tickets | quantity >= min | Quantity check |
| 88 | Date range | date in [d1, d2, d3] | Range check |
| 89 | Time range | time in [t1, t2] | Range check |
| 90 | Combined filters | All criteria must pass | Combined check |

### 3.10 Error & Edge Cases

| # | Edge Case | Error Type | Handling |
|---|-----------|-----------|----------|
| 91 | Network timeout | Page load fails | Retry or report |
| 92 | CAPTCHA | Bot detection | Report and skip |
| 93 | Rate limiting | Too many requests | Backoff and retry |
| 94 | Invalid page | Malformed HTML | Graceful fallback |
| 95 | Missing elements | Selector not found | Return null |
| 96 | Script error | JS execution fails | Catch and log |
| 97 | Cookie popup | Blocks content | Dismiss popup |
| 98 | Login required | Protected content | Report and skip |
| 99 | Geo-blocking | Region restricted | Report and skip |
| 100 | Browser crash | Session lost | Restart and retry |

---

## 4. JavaScript Scraper Specification

### 4.1 File: `stubhub_info_gathering.js`

### 4.2 Helper Functions (10 functions)

```javascript
// 1. Visibility Check
isVisible(element) → boolean
// Checks if element is visible in viewport (≥50% visible)

// 2. Recorded Tracking
isRecorded(element) → boolean
setIsRecorded(element) → void
// Prevent duplicate processing

// 3. Event Name Parsing
parseEventName(text) → string | null
// Extract and normalize event name

// 4. Date Parsing
parseDateText(text) → string | null  // Returns YYYY-MM-DD
// Handle: "Dec 20, 2025", "December 20, 2025", "12/20/25"

// 5. Time Parsing
parseTimeText(text) → string | null  // Returns HH:MM:SS
// Handle: "7:30 PM", "19:30", "TBD"

// 6. Combined Date/Time
parseDateTime(dateText, timeText) → {date, time}
// Parse and combine date and time

// 7. Venue Parsing
parseVenue(text) → {venue, city, state}
// Extract venue, city, and state

// 8. Price Parsing
parsePrice(text) → number | null
// Extract numeric price value

// 9. Ticket Count Parsing
parseTicketCount(text) → number | null
// Extract number of tickets

// 10. Section Parsing
parseSeatSection(text) → string | null
// Extract section identifier
```

### 4.3 Page Handlers (5 handlers)

```javascript
// 1. Search Results Page
handleSearchPage() → results[]
// URL Pattern: /search?q=... or /s?...
// Extracts: All search result cards

// 2. Event Detail Page
handleEventPage() → results[]
// URL Pattern: /event/{eventId}
// Extracts: Event info + ticket listings

// 3. Ticket Selection Page
handleTicketSelectionPage() → results[]
// URL Pattern: /checkout or /tickets/...
// Extracts: Selected ticket details

// 4. Category Browse Page
handleCategoryPage() → results[]
// URL Pattern: /sports/nba, /concerts/...
// Extracts: Category event listings

// 5. Artist/Venue Page
handleArtistVenuePage() → results[]
// URL Pattern: /artist/..., /venue/...
// Extracts: Artist/venue events
```

### 4.4 Output Schema

```javascript
{
    url: string,           // Current page URL
    eventName: string,     // Event name
    date: string,          // YYYY-MM-DD
    time: string,          // HH:MM:SS
    venue: string,         // Venue name
    city: string,          // City name
    section: string,       // Seat section
    row: string,           // Seat row
    price: number,         // Price in USD
    ticketCount: number,   // Number of tickets
    info: string           // "available", "sold_out", "limited"
}
```

---

## 5. Python Verifier Specification

### 5.1 File: `stubhub_info_gathering.py`

### 5.2 Main Class: `StubHubInfoGathering`

```python
class StubHubInfoGathering(BaseMetric):
    """Gather event ticket information from StubHub."""
    
    def __init__(self, queries: list[list[MultiCandidateQuery]]) -> None:
        """Initialize with expected queries."""
    
    async def reset(self) -> None:
        """Reset tracking state."""
    
    async def update(self, page: Page) -> None:
        """Process page and update coverage."""
    
    async def compute(self) -> FinalResult:
        """Calculate final coverage score."""
```

### 5.3 Query Structures

```python
class SingleCandidateQuery(TypedDict, total=False):
    event_name: str | None       # Single event name
    date: str | None             # Single date (YYYY-MM-DD)
    time: str | None             # Single time (HH:MM:SS)
    venue: str | None            # Single venue
    city: str | None             # Single city
    min_tickets: int | None      # Minimum tickets required
    max_price: float | None      # Maximum price per ticket

class MultiCandidateQuery(TypedDict, total=False):
    event_names: list[str]       # Alternative event names
    dates: list[str]             # Alternative dates
    times: list[str]             # Alternative times
    venues: list[str]            # Alternative venues
    cities: list[str]            # Alternative cities
    min_tickets: int             # Minimum tickets required
    max_price: float             # Maximum price per ticket
```

### 5.4 Result Structure

```python
class FinalResult(BaseModel):
    score: float                 # 0.0 to 1.0
    n_queries: int               # Total queries
    n_covered: int               # Queries matched
    queries: list                # Original queries
    is_query_covered: list[bool] # Per-query coverage
```

### 5.5 Matching Logic

```python
# Matching Flow:
1. Check event name (case-insensitive, any alternative)
2. Check venue/city (case-insensitive, any alternative)
3. Check date (exact match, any alternative)
4. Check time (exact match, any alternative)
5. Check price (≤ max_price if specified)
6. Check tickets (≥ min_tickets if specified)
7. Check availability (must be "available" or equivalent)

# Coverage Calculation:
score = n_covered_queries / total_queries
```

---

## 6. Query Structure

### 6.1 Simple Query Example

```python
{
    "event_names": ["lakers"],
    "dates": ["2025-12-20"],
    "cities": ["los angeles"]
}
# Matches: Lakers game on Dec 20, 2025 in LA
```

### 6.2 Complex Query Example

```python
{
    "event_names": ["lakers", "los angeles lakers", "la lakers"],
    "dates": ["2025-12-20", "2025-12-21", "2025-12-22"],
    "times": ["19:00:00", "19:30:00", "20:00:00"],
    "venues": ["crypto.com arena", "staples center"],
    "cities": ["los angeles", "la", "inglewood"],
    "min_tickets": 2,
    "max_price": 500.00
}
# Matches: Any Lakers game on Dec 20-22, 7-8 PM, ≥2 tickets, ≤$500
```

### 6.3 Multi-Query Example

```python
queries = [
    # Query 1: Lakers game
    [{
        "event_names": ["lakers"],
        "dates": ["2025-12-20"],
        "min_tickets": 2
    }],
    # Query 2: Clippers game (alternative)
    [{
        "event_names": ["clippers"],
        "dates": ["2025-12-21"],
        "min_tickets": 2
    }]
]
# Score 0.5 if one matches, 1.0 if both match
```

---

## 7. Task Generation

### 7.1 Deterministic Task Generation

```python
def generate_task_config_deterministic(
    mode: Literal["any", "all"],
    task: str,
    queries: list[list[MultiCandidateQuery]],
    location: str,
    timezone: str,
    timestamp: int | None = None,
    url: str = "https://www.stubhub.com",
) -> BaseTaskConfig:
    """Generate fixed task configuration."""
```

### 7.2 Random Task Generation

```python
def generate_task_config_random(
    event_type: Literal["sports", "concert", "theater"],
    city: str,
    seed: int | None = None,
    url: str = "https://www.stubhub.com",
) -> BaseTaskConfig:
    """Generate random task configuration."""
```

### 7.3 Date Helpers

```python
def get_next_weekend_dates() -> list[str]:
    """Get next Saturday and Sunday dates."""

def get_upcoming_weekday(weekday_name: str) -> str:
    """Get next occurrence of a weekday."""

def get_date_range(start_offset: int, end_offset: int) -> list[str]:
    """Get dates in range from today."""
```

---

## 8. Supported Event Categories

### 8.1 Sports Events

| League | Teams Covered | Venues |
|--------|---------------|--------|
| **NBA** | Lakers, Warriors, Clippers, Celtics, Heat, Knicks, Nets, Bulls, Mavericks, Suns | Crypto.com Arena, Chase Center, Madison Square Garden, etc. |
| **NFL** | 49ers, Cowboys, Patriots, Chiefs, Packers, Eagles, Rams, Chargers | SoFi Stadium, Levi's Stadium, AT&T Stadium, etc. |
| **MLB** | Dodgers, Yankees, Red Sox, Giants, Cubs, Mets, Cardinals | Dodger Stadium, Yankee Stadium, Fenway Park, etc. |
| **NHL** | Kings, Rangers, Bruins, Blackhawks, Maple Leafs, Penguins | Crypto.com Arena, Madison Square Garden, TD Garden, etc. |
| **MLS** | LA Galaxy, LAFC, Inter Miami, NYCFC | Dignity Health Sports Park, BMO Stadium, etc. |
| **NCAA** | Major college teams | Various university venues |

### 8.2 Concert Events

| Genre | Artists Covered |
|-------|-----------------|
| **Pop** | Taylor Swift, Ed Sheeran, Ariana Grande, Bruno Mars, Dua Lipa |
| **Rock** | Foo Fighters, Metallica, Green Day, Coldplay, U2 |
| **Hip-Hop** | Drake, Kendrick Lamar, Travis Scott, Kanye West |
| **Country** | Morgan Wallen, Luke Combs, Chris Stapleton |
| **R&B** | The Weeknd, SZA, Beyoncé |
| **Electronic** | Calvin Harris, Deadmau5, Marshmello |

### 8.3 Theater Events

| Category | Shows/Performers |
|----------|-----------------|
| **Broadway** | Hamilton, Wicked, The Lion King, Phantom of the Opera |
| **Comedy** | Kevin Hart, Dave Chappelle, Trevor Noah, John Mulaney |
| **Musicals** | Chicago, Les Misérables, Dear Evan Hansen |
| **Plays** | Harry Potter and the Cursed Child |

---

## 9. Venue Mappings

### 9.1 Los Angeles Area

| Venue | Address | Primary Events |
|-------|---------|----------------|
| Crypto.com Arena | 1111 S Figueroa St, LA | Lakers, Clippers, Kings, Concerts |
| SoFi Stadium | 1001 Stadium Dr, Inglewood | Rams, Chargers, NFL, Concerts |
| Dodger Stadium | 1000 Vin Scully Ave, LA | Dodgers, MLB |
| Hollywood Bowl | 2301 N Highland Ave, LA | Concerts |
| The Forum | 3900 W Manchester Blvd, Inglewood | Concerts |
| Rose Bowl | 1001 Rose Bowl Dr, Pasadena | UCLA, Events |

### 9.2 New York Area

| Venue | Address | Primary Events |
|-------|---------|----------------|
| Madison Square Garden | 4 Penn Plaza, NYC | Knicks, Rangers, Concerts |
| Yankee Stadium | 1 E 161st St, Bronx | Yankees, MLB |
| Barclays Center | 620 Atlantic Ave, Brooklyn | Nets, Concerts |
| MetLife Stadium | 1 MetLife Stadium Dr, NJ | Giants, Jets, NFL |
| Citi Field | 41 Seaver Way, Queens | Mets, Concerts |

### 9.3 San Francisco Bay Area

| Venue | Address | Primary Events |
|-------|---------|----------------|
| Chase Center | 1 Warriors Way, SF | Warriors, Concerts |
| Oracle Park | 24 Willie Mays Plaza, SF | Giants, MLB |
| Levi's Stadium | 4900 Marie P DeBartolo Way, Santa Clara | 49ers, NFL |
| Oakland Coliseum | 7000 Coliseum Way, Oakland | Events |

---

## 10. Testing Strategy

### 10.1 Unit Tests (30+ tests)

| Category | Tests | Coverage |
|----------|-------|----------|
| Event Name Parsing | 8 tests | All formats |
| Date/Time Parsing | 10 tests | All formats |
| Price Parsing | 6 tests | All formats |
| Query Matching | 8 tests | All conditions |
| Coverage Calculation | 5 tests | All scenarios |

### 10.2 Integration Tests

| Test | Description |
|------|-------------|
| Search → Event | Navigate and extract |
| Event → Tickets | Full flow |
| Multi-page | Multiple updates |
| Error handling | Graceful failures |

### 10.3 End-to-End Tests

| Test | Expected Result |
|------|-----------------|
| Lakers search | Find Lakers games |
| Concert search | Find concert tickets |
| Sold out event | Detect unavailable |
| Price filter | Filter by price |

### 10.4 Performance Targets

| Metric | Target |
|--------|--------|
| Page scrape time | < 500ms |
| Query matching | < 50ms |
| End-to-end | < 3s |
| Memory usage | < 100MB |

---

## 11. Deliverables

### 11.1 Core Files

| File | Purpose | Lines |
|------|---------|-------|
| `stubhub_info_gathering.js` | JavaScript scraper | ~400 |
| `stubhub_info_gathering.py` | Python verifier | ~600 |
| `__init__.py` | Module exports | ~15 |

### 11.2 Test Files

| File | Purpose | Lines |
|------|---------|-------|
| `test_stubhub.py` | Test suite | ~200 |
| `test_edge_cases.py` | Edge case tests | ~300 |

### 11.3 Documentation

| File | Purpose |
|------|---------|
| `README.md` | API documentation |
| `TEST_GUIDE.md` | Testing instructions |
| `EDGE_CASES.md` | Edge case catalog |

### 11.4 Total Deliverables

- **6-8 files**
- **~1,500+ lines of code**
- **100+ edge cases covered**
- **30+ unit tests**
- **Complete documentation**

---

## 12. Timeline

| Phase | Duration | Deliverables |
|-------|----------|--------------|
| Research & Planning | 1 day | DOM selectors, edge case catalog |
| JavaScript Scraper | 2 days | Complete scraper with all handlers |
| Python Verifier | 2 days | Complete matching logic |
| Task Generation | 1 day | All task generation functions |
| Testing | 2 days | Unit + integration + E2E tests |
| Documentation | 1 day | Complete documentation |
| **Total** | **9 days** | **Production-ready verifier** |

---

## Appendix A: DOM Selectors

### Search Results Page
```javascript
// Event cards
'[data-testid="search-result-item"]'
'[data-testid="event-name"]'
'[data-testid="event-date"]'
'[data-testid="venue-name"]'
'[data-testid="price"]'
```

### Event Detail Page
```javascript
// Event header
'h1'  // Event name
'[class*="EventHeader"]'  // Date, time, venue
'#stubhub-event-detail-listings-scroll-container'  // Ticket listings
```

### Ticket Listings
```javascript
'[data-testid="listing-row"]'
'[data-testid="section"]'
'[data-testid="price"]'
'[data-testid="quantity"]'
```

---

## Appendix B: Sample Dataset Items

### Sports Event
```json
{
    "task_id": "navi_bench/stubhub/sports/lakers/0",
    "task_generation_config_json": {
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
        "timezone": "America/Los_Angeles"
    },
    "env": "real",
    "domain": "stubhub",
    "l1_category": "entertainment",
    "l2_category": "sports"
}
```

### Concert Event
```json
{
    "task_id": "navi_bench/stubhub/concert/taylor-swift/0",
    "task_generation_config_json": {
        "_target_": "navi_bench.stubhub.stubhub_info_gathering.generate_task_config_deterministic",
        "mode": "any",
        "url": "https://www.stubhub.com",
        "task": "Find Taylor Swift Eras Tour tickets for any date with at least 2 tickets",
        "queries": [[{
            "event_names": ["taylor swift", "eras tour"],
            "min_tickets": 2
        }]],
        "location": "Los Angeles, CA, United States",
        "timezone": "America/Los_Angeles"
    },
    "env": "real",
    "domain": "stubhub",
    "l1_category": "entertainment",
    "l2_category": "concerts"
}
```

---

## Appendix C: Error Handling

| Error | Detection | Handling |
|-------|-----------|----------|
| Page not found | 404 status | Return empty results |
| Network timeout | No response | Retry up to 3 times |
| CAPTCHA | Specific element | Report and skip |
| Rate limit | 429 status | Backoff and retry |
| Invalid data | Parsing fails | Log and continue |
| Empty results | No elements | Return empty array |

---

## Appendix D: Performance Benchmarks

| Operation | Expected Time |
|-----------|--------------|
| Page load | 1-2 seconds |
| DOM scraping | 100-500ms |
| Query matching | 10-50ms |
| Total per page | < 3 seconds |

---

**Document Version:** 1.0  
**Last Updated:** December 19, 2025  
**Author:** Navi-Bench Development Team  
**Status:** Complete Specification
