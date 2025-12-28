# StubHub Ticket Verifier

A production-level web scraper and verifier for StubHub event ticket pages. This module extracts event information and validates user navigation to specific events.

---

## 📁 Files Overview

| File | Description |
|------|-------------|
| `stubhub_info_gathering.js` | JavaScript scraper injected into browser to extract event data |
| `stubhub_info_gathering.py` | Python verifier with query matching logic |
| `demo_stubhub.py` | Interactive demo for manual testing |
| `auto_demo_stubhub.py` | Automated demo script |
| `test_stubhub_unit.py` | Unit tests (20 tests) |

---

## 🚀 Quick Start

```bash
cd navi_bench/stubhub
python demo_stubhub.py
```

---

## ✅ Features Covered

### Event Data Extraction
- ✅ Event name from URL slug, headings, and page content
- ✅ Event category detection (concerts, sports, theater, comedy)
- ✅ Venue and city extraction
- ✅ Date and time parsing (including relative dates: today, tomorrow)
- ✅ Ticket pricing and currency detection (USD, INR, EUR, GBP)

### Ticket Details
- ✅ Section, zone, and row extraction
- ✅ Seat numbers and aisle seat detection
- ✅ VIP and accessible seating detection
- ✅ Delivery type (electronic, physical, will_call)
- ✅ Ticket quantity from URL parameters

### URL-Based Verification
- ✅ URL section/zone filters
- ✅ URL quantity parameters
- ✅ URL ticket class detection
- ✅ URL price range parsing
- ✅ URL sort order detection

### Page State Detection
- ✅ Login status (logged_in, logged_out)
- ✅ Page type (event_listing, event_category, checkout, event_modal)
- ✅ Availability status (available, sold_out, presale, get_notified)
- ✅ Loading state and spinner detection
- ✅ Filter panel state

### Advanced Detection
- ✅ Geo-blocking detection
- ✅ CAPTCHA detection
- ✅ Seller rating and type
- ✅ Resale vs face value tickets
- ✅ Obstructed view warnings
- ✅ Age restrictions

---

## 🔒 Strict Verification Logic

### URL-Based Page Detection
The verifier distinguishes between page types:

```javascript
const isEventPage = currentUrl.includes('/event/');
const isCategoryPage = currentUrl.includes('/category/');
```

| Page Type | URL Pattern | Behavior |
|-----------|-------------|----------|
| Category | `/category/` or `-tickets` | Returns only main artist, no city |
| Event | `/event/12345/` | Returns full event with city |

### City Requirement
When query specifies `cities`, info **must** have a matching city:

```python
if cities := query.get("cities"):
    if not city:
        return False  # Must have city
```

---

## 🧪 Testing

```bash
# Run all unit tests
python -m pytest test_stubhub_unit.py -v

# Check JS syntax
node --check stubhub_info_gathering.js
```

**Test Status:** ✅ 20/20 tests passing

---

## 📊 Query Configuration

Example query for Zakir Khan events in Mumbai/Pune:

```python
queries = [[{
    "event_names": ["zakir khan", "zakir"],
    "cities": ["mumbai", "pune"],
    "require_available": False,  # Credit for sold-out events too
}]]
```

### Available Query Fields

| Field | Type | Description |
|-------|------|-------------|
| `event_names` | list[str] | Event name keywords |
| `event_categories` | list[str] | concerts, sports, theater, comedy |
| `cities` | list[str] | Required cities |
| `venues` | list[str] | Venue names |
| `dates` | list[str] | Specific dates |
| `date_range` | str | today, this-weekend, this-week |
| `min_price` / `max_price` | float | Price range |
| `ticket_quantities` | list[int] | Exact ticket counts |
| `require_available` | bool | Require tickets available |
| `require_page_type` | str/list | event_listing, checkout, etc. |

---

## 🎯 Verification Outcomes

| User Location | Score | Reason |
|---------------|-------|--------|
| Category page (no click) | 0% | No city extracted |
| Event page, wrong city | 0% | City doesn't match |
| Event page, correct city | 100% | All criteria match |
| Sold-out (Get Notified) | 0% | URL doesn't change |

---

## 📝 Related Documentation

- [FINAL_IMPLEMENTATION_DOC.md](./FINAL_IMPLEMENTATION_DOC.md) - Detailed implementation notes
- [fnal_doc.md](./fnal_doc.md) - Original edge case specification
- [TEST_GUIDE.md](./TEST_GUIDE.md) - Testing guide

---

## 🛠️ Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Browser                          │
│  ┌───────────────────────────────────────────────┐  │
│  │         stubhub_info_gathering.js             │  │
│  │  - Scrapes DOM for event data                 │  │
│  │  - Detects page type from URL                 │  │
│  │  - Returns extracted info as JSON             │  │
│  └───────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────┘
                         │ JSON
                         ▼
┌─────────────────────────────────────────────────────┐
│              stubhub_info_gathering.py              │
│  ┌───────────────────────────────────────────────┐  │
│  │         StubHubInfoGathering Class            │  │
│  │  - update(): Collects scraped data            │  │
│  │  - compute(): Matches against queries         │  │
│  │  - Returns score (0-100%)                     │  │
│  └───────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

---

## 📌 Important Notes

1. **Sold-out events** open modals without URL change → Cannot verify specific city
2. **Available events** navigate to `/event/` URL → Can verify city
3. **City is required** when `cities` filter is in query
4. **Event name** is extracted from URL slug (most reliable)

---

## 🔧 Maintenance

To add new fields:
1. Add extraction logic in `stubhub_info_gathering.js`
2. Add field to `InfoDict` in `stubhub_info_gathering.py`
3. Add query field to `MultiCandidateQuery` if filterable
4. Add matching logic in `_check_multi_candidate_query()`
5. Add unit test in `test_stubhub_unit.py`
