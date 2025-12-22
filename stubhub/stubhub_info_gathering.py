"""StubHub info gathering verifier for event ticket searches.

This module provides functionality to verify AI agent ticket search results on StubHub
by gathering event information through JavaScript scraping and matching against expected queries.
"""

import functools
import itertools
import random
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Literal
from zoneinfo import ZoneInfo

from beartype import beartype
from loguru import logger
from playwright.async_api import Page
from pydantic import BaseModel
from typing_extensions import TypedDict

from navi_bench.base import BaseMetric, BaseTaskConfig, UserMetadata, get_import_path
from navi_bench.dates import initialize_placeholder_map, initialize_user_metadata, render_task_statement


class SingleCandidateQuery(TypedDict, total=False):
    """Single event query with specific criteria."""
    # Event Search Filters
    event_name: str | None
    event_category: str | None  # concerts, sports, theater, comedy, festivals
    date: str | None
    time: str | None
    venue: str | None
    city: str | None
    
    # Ticket Listing Filters
    min_tickets: int | None
    max_price: float | None
    min_price: float | None
    section: str | None
    zone: str | None
    row: str | None
    aisle_seat: bool | None
    
    # Ticket Type Filters
    ticket_type: str | None  # standard, vip, premium, general_admission, standing, seated
    parking_only: bool | None
    accessible_seating: bool | None
    
    # Delivery Filters
    delivery_type: str | None  # instant_download, electronic, mobile_transfer, physical, will_call
    instant_download_only: bool | None
    
    # Special Filters
    vip_packages: bool | None
    includes_extras: bool | None
    price_with_fees: bool | None
    
    # Sorting
    sort_order: str | None  # recommended, price_low_to_high, price_high_to_low, best_value, best_seats


class MultiCandidateQuery(TypedDict, total=False):
    """Multi-option event query allowing alternatives."""
    # Event Search Filters
    event_names: list[str] | None
    event_categories: list[str] | None  # concerts, sports, theater, comedy, festivals
    dates: list[str] | None
    date_range: str | None  # today, this-weekend, this-week, this-month
    times: list[str] | None
    venues: list[str] | None
    cities: list[str] | None
    
    # Ticket Listing Filters
    min_tickets: int | None
    max_tickets: int | None
    max_price: float | None
    min_price: float | None
    sections: list[str] | None
    zones: list[str] | None  # Lower Level, Upper Deck, Floor, etc.
    rows: list[str] | None
    aisle_seat: bool | None
    
    # Ticket Type Filters
    ticket_types: list[str] | None  # standard, vip, premium, general_admission, standing, seated
    parking_only: bool | None
    accessible_seating: bool | None
    
    # Delivery Filters
    delivery_types: list[str] | None  # instant_download, electronic, mobile_transfer, physical, will_call
    instant_download_only: bool | None
    
    # Special Filters
    vip_packages: bool | None
    includes_extras: bool | None
    price_with_fees: bool | None
    
    # Sorting
    sort_order: str | None  # recommended, price_low_to_high, price_high_to_low, best_value, best_seats


class InputDict(TypedDict, total=False):
    """Input for update method."""
    page: Page


class InfoDict(TypedDict, total=False):
    """Scraped event information from JavaScript - comprehensive."""
    # Basic Info
    url: str
    eventName: str
    eventCategory: str  # concerts, sports, theater, comedy, festivals
    
    # Date/Time
    date: str
    time: str
    dateRange: str  # today, this-weekend, this-week, this-month
    
    # Location
    venue: str
    city: str
    state: str
    country: str
    
    # Ticket Details
    section: str
    zone: str
    row: str
    seat: str
    aisleSeay: bool
    
    # Pricing
    price: float
    priceWithFees: float
    faceValue: float
    
    # Quantity
    ticketCount: int
    availableQuantities: list[int]
    
    # Ticket Type
    ticketType: str  # standard, vip, premium, general_admission
    isVIP: bool
    isAccessible: bool
    isParkingPass: bool
    
    # Delivery
    deliveryType: str  # instant_download, electronic, mobile_transfer, physical, will_call
    isInstantDownload: bool
    
    # Extras
    includesExtras: bool
    extraDetails: str
    
    # Availability Status
    info: str  # available, sold_out, limited, waitlist, presale
    totalListings: int
    
    # Seller Info
    sellerRating: float
    sellerType: str  # individual, professional



class FinalResult(BaseModel):
    """Final verification result."""
    score: float
    n_queries: int
    n_covered: int
    queries: list[list[MultiCandidateQuery]]
    is_query_covered: list[bool]


@beartype
class StubHubInfoGathering(BaseMetric):
    """Gather event ticket information from StubHub to evaluate query coverage."""

    def __init__(self, queries: list[list[MultiCandidateQuery]]) -> None:
        super().__init__()
        self.queries = queries
        self._all_infos: list[list[InfoDict]] = []
        self._is_query_covered: list[bool] = [False] * len(queries)
        self._unavailable_evidences: list[list[list[InfoDict]]] = [
            [[] for _ in alternative_conditions] for alternative_conditions in queries
        ]

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(queries={self.queries})"

    @functools.cached_property
    def js_script(self) -> str:
        """Load the JavaScript scraper."""
        with open(Path(__file__).parent / "stubhub_info_gathering.js", "r") as f:
            return f.read()

    async def reset(self) -> None:
        """Reset all tracking state."""
        self._all_infos = []
        self._is_query_covered = [False] * len(self.queries)
        self._unavailable_evidences = [[[] for _ in alternative_conditions] for alternative_conditions in self.queries]

    async def update(self, **kwargs) -> None:
        """Update with new page information."""
        inputs: InputDict = kwargs
        page = inputs["page"]
        infos: list[InfoDict] = await page.evaluate(self.js_script)
        logger.info(f"StubHubInfoGathering.update gathered {len(infos)} intermediate infos: {infos}")

        self._all_infos.append(infos)

        for i, alternative_conditions in enumerate(self.queries):
            if self._is_query_covered[i]:
                continue

            for info in infos:
                if self._check_alternative_conditions(i, alternative_conditions, info):
                    logger.info(
                        f"StubHubInfoGathering.update found {i}-th query covered: {alternative_conditions=}, {info=}"
                    )
                    self._is_query_covered[i] = True
                    break

    async def compute(self) -> FinalResult:
        """Compute final coverage score."""
        for i, alternative_conditions in enumerate(self.queries):
            if self._is_query_covered[i]:
                continue
            for j, alternative_condition in enumerate(alternative_conditions):
                if not self._is_exhausted(alternative_condition, self._unavailable_evidences[i][j]):
                    break
            else:
                logger.info(f"StubHubInfoGathering.compute found {i}-th query exhausted: {alternative_conditions=}")
                self._is_query_covered[i] = True

        n_queries = len(self.queries)
        n_covered = sum(self._is_query_covered)
        final_result = FinalResult(
            score=n_covered / max(n_queries, 1),
            n_queries=n_queries,
            n_covered=n_covered,
            queries=self.queries,
            is_query_covered=self._is_query_covered,
        )
        logger.info(f"StubHubInfoGathering.compute final result: {final_result}")
        return final_result

    def _check_alternative_conditions(
        self, i: int, alternative_conditions: list[MultiCandidateQuery], info: InfoDict
    ) -> bool:
        """Check if any alternative condition is covered by the info."""
        for j, alternative_condition in enumerate(alternative_conditions):
            evidences = self._unavailable_evidences[i][j]
            if self._check_multi_candidate_query(alternative_condition, info, evidences):
                return True
        return False

    @classmethod
    def _check_multi_candidate_query(
        cls, query: MultiCandidateQuery, info: InfoDict, evidences: list[InfoDict]
    ) -> bool:
        """Check if the multi-candidate query matches the info - comprehensive filter matching."""
        
        # ========== EVENT SEARCH FILTERS ==========
        
        # Check event names using SUBSTRING matching
        if query_names := query.get("event_names"):
            query_names = [name.lower() for name in query_names]
            event_name = info.get("eventName", "").lower()
            if not any(qname in event_name for qname in query_names):
                return False

        # Check event categories
        if query_categories := query.get("event_categories"):
            query_categories = [c.lower() for c in query_categories]
            event_category = info.get("eventCategory", "").lower()
            if event_category and not any(c in event_category for c in query_categories):
                return False

        # Check venues using SUBSTRING matching
        if venues := query.get("venues"):
            venues = [v.lower() for v in venues]
            venue = info.get("venue", "").lower()
            if venue and not any(v in venue for v in venues):
                return False

        # Check cities using SUBSTRING matching
        if cities := query.get("cities"):
            cities = [c.lower() for c in cities]
            city = info.get("city", "").lower()
            if city and not any(c in city for c in cities):
                return False

        # ========== TICKET LISTING FILTERS ==========
        
        # Check minimum tickets
        if min_tickets := query.get("min_tickets"):
            ticket_count = info.get("ticketCount", 0)
            if ticket_count and ticket_count < min_tickets:
                return False

        # Check maximum tickets
        if max_tickets := query.get("max_tickets"):
            ticket_count = info.get("ticketCount", 0)
            if ticket_count and ticket_count > max_tickets:
                return False

        # Check maximum price
        if max_price := query.get("max_price"):
            # Check both regular price and price with fees
            price = info.get("price") or info.get("priceWithFees")
            if price is not None and price > max_price:
                return False

        # Check minimum price
        if min_price := query.get("min_price"):
            price = info.get("price") or info.get("priceWithFees")
            if price is not None and price < min_price:
                return False

        # Check sections using SUBSTRING matching
        if sections := query.get("sections"):
            sections = [s.lower() for s in sections]
            section = info.get("section", "").lower()
            if section and not any(s in section for s in sections):
                return False

        # Check zones using SUBSTRING matching
        if zones := query.get("zones"):
            zones = [z.lower() for z in zones]
            zone = info.get("zone", "").lower()
            if zone and not any(z in zone for z in zones):
                return False

        # Check rows using SUBSTRING matching
        if rows := query.get("rows"):
            rows = [r.lower() for r in rows]
            row = info.get("row", "").lower()
            if row and not any(r in row for r in rows):
                return False

        # Check aisle seat requirement
        if query.get("aisle_seat") is True:
            if not info.get("aisleSeat", False):
                return False

        # ========== TICKET TYPE FILTERS ==========
        
        # Check ticket types
        if ticket_types := query.get("ticket_types"):
            ticket_types = [t.lower() for t in ticket_types]
            ticket_type = info.get("ticketType", "").lower()
            if ticket_type and not any(t in ticket_type for t in ticket_types):
                return False

        # Check parking only filter
        if query.get("parking_only") is True:
            if not info.get("isParkingPass", False):
                return False

        # Check accessible seating requirement
        if query.get("accessible_seating") is True:
            if not info.get("isAccessible", False):
                return False

        # ========== DELIVERY FILTERS ==========
        
        # Check delivery types
        if delivery_types := query.get("delivery_types"):
            delivery_types = [d.lower() for d in delivery_types]
            delivery_type = info.get("deliveryType", "").lower()
            if delivery_type and not any(d in delivery_type for d in delivery_types):
                return False

        # Check instant download only
        if query.get("instant_download_only") is True:
            if not info.get("isInstantDownload", False):
                return False

        # ========== SPECIAL FILTERS ==========
        
        # Check VIP packages
        if query.get("vip_packages") is True:
            if not info.get("isVIP", False):
                return False

        # Check includes extras
        if query.get("includes_extras") is True:
            if not info.get("includesExtras", False):
                return False

        # ========== DATE/TIME FILTERS ==========
        
        query_dates = query.get("dates")
        query_times = query.get("times")
        query_date_range = query.get("date_range")

        available_info = info.get("info", "").lower()

        # Handle date range (today, this-weekend, this-week, this-month)
        if query_date_range:
            info_date_range = info.get("dateRange", "").lower()
            if info_date_range and query_date_range.lower() not in info_date_range:
                # If no match on date range text, skip this check
                pass

        # Handle sold out / unavailable events
        if "sold_out" in available_info or "unavailable" in available_info:
            if query_dates:
                if info.get("date") in query_dates:
                    evidences.append(info)
                    return False
            if query_times:
                if info.get("time") in query_times:
                    evidences.append(info)
                    return False
            return False
        else:
            # Event is available - check date/time match
            if query_dates:
                if info.get("date") not in query_dates:
                    return False
            if query_times:
                if info.get("time") not in query_times:
                    return False
            return True


    @classmethod
    def _check_single_candidate_query(cls, query: SingleCandidateQuery, info: InfoDict) -> bool:
        """Check if single-candidate query matches the info."""
        if (query_name := query.get("event_name")) is not None:
            if info.get("eventName", "").lower() != query_name.lower():
                return False

        if (query_venue := query.get("venue")) is not None:
            if info.get("venue", "").lower() != query_venue.lower():
                return False

        if (query_city := query.get("city")) is not None:
            if info.get("city", "").lower() != query_city.lower():
                return False

        if (query_min_tickets := query.get("min_tickets")) is not None:
            if info.get("ticketCount", 0) < query_min_tickets:
                return False

        if (query_max_price := query.get("max_price")) is not None:
            if info.get("price", float('inf')) > query_max_price:
                return False

        query_date = query.get("date")
        query_time = query.get("time")

        if "sold_out" in info.get("info", "").lower():
            if query_date:
                if info.get("date") == query_date:
                    return True
            if query_time:
                if info.get("time") == query_time:
                    return True
            return False
        else:
            if query_date:
                if info.get("date") != query_date:
                    return False
            if query_time:
                if info.get("time") != query_time:
                    return False
            return True

    @classmethod
    def _is_exhausted(cls, query: MultiCandidateQuery, evidences: list[InfoDict]) -> bool:
        """Check if we've exhausted searching for the query."""
        query_names = query.get("event_names") or [None]
        query_venues = query.get("venues") or [None]
        query_cities = query.get("cities") or [None]
        query_dates = query.get("dates") or [None]
        query_times = query.get("times") or [None]

        for query_name, query_venue, query_city, query_date, query_time in itertools.product(
            query_names, query_venues, query_cities, query_dates, query_times
        ):
            found_match = False
            for info in evidences:
                if cls._check_single_candidate_query(
                    SingleCandidateQuery(
                        event_name=query_name,
                        venue=query_venue,
                        city=query_city,
                        date=query_date,
                        time=query_time,
                    ),
                    info,
                ):
                    found_match = True
                    break

            if not found_match:
                return False

        return True


# Event categories and metadata
EVENT_CATEGORIES = {
    "sports": {
        "nba": ["Lakers", "Warriors", "Clippers", "Celtics", "Heat"],
        "nfl": ["49ers", "Cowboys", "Patriots", "Chiefs", "Packers"],
        "mlb": ["Dodgers", "Yankees", "Red Sox", "Giants", "Cubs"],
        "nhl": ["Kings", "Rangers", "Bruins", "Blackhawks", "Maple Leafs"],
    },
    "concert": {
        "pop": ["Taylor Swift", "Ed Sheeran", "Ariana Grande"],
        "rock": ["Foo Fighters", "Metallica", "Green Day"],
        "hip-hop": ["Drake", "Kendrick Lamar", "Travis Scott"],
    },
    "theater": {
        "broadway": ["Hamilton", "Wicked", "The Lion King"],
        "comedy": ["Kevin Hart", "Dave Chappelle", "Trevor Noah"],
    },
}

# City to venue mappings
CITY_VENUES = {
    "Los Angeles": {
        "location": "Los Angeles, CA, United States",
        "timezone": "America/Los_Angeles",
        "venues": {
            "Crypto.com Arena": ["Lakers", "Clippers", "Kings"],
            "SoFi Stadium": ["Rams", "Chargers"],
            "Dodger Stadium": ["Dodgers"],
            "Hollywood Bowl": ["concerts"],
        }
    },
    "New York": {
        "location": "New York, NY, United States",
        "timezone": "America/New_York",
        "venues": {
            "Madison Square Garden": ["Knicks", "Rangers"],
            "Yankee Stadium": ["Yankees"],
            "Barclays Center": ["Nets"],
        }
    },
    "San Francisco": {
        "location": "San Francisco, CA, United States",
        "timezone": "America/Los_Angeles",
        "venues": {
            "Chase Center": ["Warriors"],
            "Oracle Park": ["Giants"],
            "Levi's Stadium": ["49ers"],
        }
    },
}


def get_next_weekend_dates() -> list[str]:
    """Get dates for the next weekend (Saturday and Sunday)."""
    today = datetime.now()
    days_until_saturday = (5 - today.weekday()) % 7
    if days_until_saturday == 0:
        days_until_saturday = 7
    
    saturday = today + timedelta(days=days_until_saturday)
    sunday = saturday + timedelta(days=1)
    
    return [
        saturday.strftime("%Y-%m-%d"),
        sunday.strftime("%Y-%m-%d")
    ]


def get_upcoming_weekday(weekday_name: str) -> str:
    """Get date for the next occurrence of a weekday."""
    weekday_map = {
        "Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3,
        "Friday": 4, "Saturday": 5, "Sunday": 6
    }
    
    target_day = weekday_map[weekday_name]
    today = datetime.now()
    days_ahead = (target_day - today.weekday()) % 7
    
    if days_ahead == 0:
        days_ahead = 7
    
    target_date = today + timedelta(days=days_ahead)
    return target_date.strftime("%Y-%m-%d")


def generate_task_config_random(
    event_type: Literal["sports", "concert", "theater"],
    city: str,
    seed: int | None = None,
    url: str = "https://www.stubhub.com",
) -> BaseTaskConfig:
    """Generate random task configuration for StubHub events."""
    if seed is not None:
        random.seed(seed)

    # Get city metadata
    city_meta = CITY_VENUES.get(city, {
        "location": f"{city}, United States",
        "timezone": "America/Los_Angeles",
        "venues": {}
    })

    # Select random event based on type
    if event_type == "sports":
        sport_type = random.choice(list(EVENT_CATEGORIES["sports"].keys()))
        event_name = random.choice(EVENT_CATEGORIES["sports"][sport_type])
    elif event_type == "concert":
        genre = random.choice(list(EVENT_CATEGORIES["concert"].keys()))
        event_name = random.choice(EVENT_CATEGORIES["concert"][genre])
    else:  # theater
        category = random.choice(list(EVENT_CATEGORIES["theater"].keys()))
        event_name = random.choice(EVENT_CATEGORIES["theater"][category])

    # Generate random date (next 30 days)
    days_ahead = random.randint(1, 30)
    event_date = (datetime.now() + timedelta(days=days_ahead)).strftime("%Y-%m-%d")

    # Random price range
    max_price = random.choice([200.0, 300.0, 500.0, 1000.0])

    # Random ticket count
    min_tickets = random.randint(1, 4)

    # Create task description
    task = (
        f"Search for {event_name} tickets in {city} "
        f"for {event_date} with at least {min_tickets} tickets "
        f"under ${max_price:.0f}"
    )

    user_metadata = UserMetadata(
        location=city_meta["location"],
        timezone=city_meta["timezone"],
        timestamp=int(datetime.now().timestamp()),
    )

    eval_config = {
        "_target_": get_import_path(StubHubInfoGathering),
        "queries": [[{
            "event_names": [event_name.lower()],
            "dates": [event_date],
            "cities": [city.lower()],
            "min_tickets": min_tickets,
            "max_price": max_price,
        }]]
    }

    return BaseTaskConfig(url=url, task=task, user_metadata=user_metadata, eval_config=eval_config)


def generate_task_config_deterministic(
    mode: Literal["any", "all"],
    task: str,
    queries: list[list[MultiCandidateQuery]],
    location: str,
    timezone: str,
    timestamp: int | None = None,
    url: str = "https://www.stubhub.com",
) -> BaseTaskConfig:
    """Generate deterministic task configuration."""
    user_metadata = initialize_user_metadata(timezone, location, timestamp)
    
    eval_config = {
        "_target_": get_import_path(StubHubInfoGathering),
        "queries": queries
    }

    return BaseTaskConfig(url=url, task=task, user_metadata=user_metadata, eval_config=eval_config)



if __name__ == "__main__":
    import json
    from navi_bench.base import DatasetItem, instantiate

    dataset_row = {
        "task_id": "navi_bench/stubhub/test/0",
        "task_generation_config_json": json.dumps({
            "_target_": "navi_bench.stubhub.stubhub_info_gathering.generate_task_config_deterministic",
            "mode": "any",
            "url": "https://www.stubhub.com",
            "task": "Search for Lakers tickets in Los Angeles for December 20, 2025",
            "queries": [[{
                "event_names": ["lakers", "los angeles lakers"],
                "dates": ["2025-12-20"],
                "cities": ["los angeles", "inglewood"]
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

    print("Loaded dataset item")
    print("-------------------")
    print(dataset_item)
    print()

    print("Generated task config")
    print("---------------------")
    print(task_config)
    print()

    print("Instantiated evaluator")
    print("----------------------")
    print(evaluator)
