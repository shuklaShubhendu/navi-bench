#!/usr/bin/env python
"""
StubHub Ticket Availability Verification Demo

Human-in-the-loop verification system for StubHub events.
Supports multi-tab browsing, real-time navigation tracking, and comprehensive
evaluation of agent navigation behavior.

Features:
- Real-time page state tracking via navigation events
- Multi-tab/popup window support
- Stealth browser configuration (anti-detection)
- Comprehensive scraper with LD+JSON extraction
- Flexible query-based verification

Author: NaviBench Team
"""

import asyncio
import json
import sys
from datetime import datetime
from typing import Any, Callable, Optional
from dataclasses import dataclass, field

from playwright.async_api import Page, BrowserContext, async_playwright
from loguru import logger

# Import our evaluator
from navi_bench.stubhub.stubhub_info_gathering import (
    StubHubInfoGathering,
    generate_task_config_deterministic,
)


# =============================================================================
# CONFIGURATION
# =============================================================================

@dataclass
class BrowserConfig:
    """Browser launch configuration for stealth operation."""
    headless: bool = False
    viewport_width: int = 1366
    viewport_height: int = 768
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    locale: str = "en-US"
    
    # Anti-detection arguments
    launch_args: list = field(default_factory=lambda: [
        "--disable-blink-features=AutomationControlled",
        "--disable-infobars",
        "--start-maximized",
        "--no-sandbox",
    ])


@dataclass
class TaskScenario:
    """Defines a verification task scenario."""
    task_id: str
    name: str
    description: str
    url: str
    task_prompt: str
    queries: list
    location: str
    timezone: str
    category: str
    tags: list = field(default_factory=list)
    
    def __post_init__(self):
        """Validate scenario configuration."""
        assert self.task_id, "task_id is required"
        assert self.queries, "queries cannot be empty"


# =============================================================================
# TASK SCENARIOS - Define your test cases here
# =============================================================================

SCENARIOS: list[TaskScenario] = [
    TaskScenario(
        task_id="stubhub/sports/nba/001",
        name="NBA Game Ticket Verification",
        description="Verify NBA basketball game ticket availability",
        url="https://www.stubhub.com/",
        task_prompt=(
            "Search for any NBA basketball game tickets. "
            "Navigate to an event page and verify ticket availability."
        ),
        queries=[[{
            "event_names": ["nba", "basketball"],
            "event_categories": ["sports"],
            "require_available": False,
        }]],
        location="United States",
        timezone="America/New_York",
        category="sports",
        tags=["nba", "basketball", "sports"],
    ),
    TaskScenario(
        task_id="stubhub/concerts/general/001",
        name="Concert Ticket Verification",
        description="Verify concert ticket availability",
        url="https://www.stubhub.com/",
        task_prompt=(
            "Search for any upcoming concert. "
            "Find an event and verify ticket availability and pricing."
        ),
        queries=[[{
            "event_categories": ["concerts"],
            "require_available": False,
        }]],
        location="United States",
        timezone="America/Los_Angeles",
        category="concerts",
        tags=["music", "concert", "live"],
    ),
    TaskScenario(
        task_id="stubhub/theater/broadway/001",
        name="Theater Show Verification",
        description="Verify Broadway/theater ticket availability",
        url="https://www.stubhub.com/",
        task_prompt=(
            "Search for any Broadway or theater show. "
            "Navigate to the event and check available tickets."
        ),
        queries=[[{
            "event_categories": ["theater"],
            "require_available": False,
        }]],
        location="New York, NY, United States",
        timezone="America/New_York",
        category="theater",
        tags=["broadway", "theater", "show"],
    ),
]


# =============================================================================
# NAVIGATION TRACKER - Real-time page state monitoring
# =============================================================================

class NavigationTracker:
    """
    Tracks navigation events across all pages in a browser context.
    Provides real-time updates to the evaluator as the user navigates.
    """
    
    def __init__(self, evaluator: StubHubInfoGathering, verbose: bool = True):
        self.evaluator = evaluator
        self.verbose = verbose
        self.navigation_count = 0
        self.pages_tracked: set[int] = set()
        self._lock = asyncio.Lock()
    
    async def attach_to_page(self, page: Page) -> None:
        """Attach navigation tracking to a page."""
        page_id = id(page)
        
        if page_id in self.pages_tracked:
            return
        
        self.pages_tracked.add(page_id)
        
        async def on_frame_navigated(frame):
            """Handle frame navigation events."""
            if frame != page.main_frame:
                return  # Only track main frame
            
            async with self._lock:
                self.navigation_count += 1
                url = page.url
                
                if self.verbose:
                    logger.info(f"[NAV #{self.navigation_count}] {url[:80]}...")
                
                try:
                    await self.evaluator.update(page=page)
                except Exception as e:
                    if self.verbose:
                        logger.warning(f"Evaluator update failed: {e}")
        
        page.on("framenavigated", lambda f: asyncio.create_task(on_frame_navigated(f)))
        
        if self.verbose:
            logger.info(f"Tracking attached to page: {page.url[:60]}...")
    
    async def handle_new_page(self, new_page: Page) -> None:
        """Handle new tab/popup windows."""
        try:
            await new_page.wait_for_load_state("domcontentloaded", timeout=10000)
            
            if self.verbose:
                logger.info(f"[NEW TAB] {new_page.url[:60]}...")
            
            await self.attach_to_page(new_page)
            await self.evaluator.update(page=new_page)
            
        except Exception as e:
            if self.verbose:
                logger.warning(f"New tab handling failed: {e}")
    
    def attach_to_context(self, context: BrowserContext) -> None:
        """Attach tracking to all new pages in a browser context."""
        context.on("page", lambda p: asyncio.create_task(self.handle_new_page(p)))


# =============================================================================
# BROWSER MANAGER - Stealth browser configuration
# =============================================================================

class BrowserManager:
    """Manages browser lifecycle with stealth configuration."""
    
    def __init__(self, config: BrowserConfig = None):
        self.config = config or BrowserConfig()
        self.browser = None
        self.context = None
        self.page = None
    
    async def launch(self, playwright) -> tuple:
        """Launch browser with stealth configuration."""
        self.browser = await playwright.chromium.launch(
            headless=self.config.headless,
            args=self.config.launch_args,
        )
        
        self.context = await self.browser.new_context(
            viewport={
                "width": self.config.viewport_width,
                "height": self.config.viewport_height
            },
            user_agent=self.config.user_agent,
            locale=self.config.locale,
        )
        
        # Anti-detection scripts
        await self.context.add_init_script("""
            // Hide webdriver property
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            
            // Override chrome.runtime
            window.chrome = { runtime: {} };
            
            // Override permissions query
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
        """)
        
        self.page = await self.context.new_page()
        
        return self.browser, self.context, self.page
    
    async def close(self) -> None:
        """Close browser and cleanup."""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()


# =============================================================================
# RESULT REPORTER - Format and display results
# =============================================================================

class ResultReporter:
    """Formats and displays verification results."""
    
    @staticmethod
    def print_header(scenario: TaskScenario) -> None:
        """Print task header."""
        print("\n" + "=" * 80)
        print(f"STUBHUB VERIFICATION: {scenario.name}")
        print("=" * 80)
        print(f"Task ID:     {scenario.task_id}")
        print(f"Category:    {scenario.category}")
        print(f"Location:    {scenario.location}")
        print(f"Timezone:    {scenario.timezone}")
        print("-" * 80)
        print(f"TASK: {scenario.task_prompt}")
        print("=" * 80)
    
    @staticmethod
    def print_instructions() -> None:
        """Print user instructions."""
        print("\n" + "-" * 40)
        print("INSTRUCTIONS:")
        print("-" * 40)
        print("1. Use the StubHub website to complete the task")
        print("2. Search for events and navigate to listings")
        print("3. The system tracks your navigation automatically")
        print("4. Press ENTER when ready to see verification results")
        print("-" * 40 + "\n")
    
    @staticmethod
    def print_result(result, tracker: NavigationTracker) -> None:
        """Print verification result."""
        print("\n" + "=" * 80)
        print("VERIFICATION RESULT")
        print("=" * 80)
        
        score_pct = result.score * 100
        status = "✅ PASS" if result.score >= 1.0 else "⚠️ PARTIAL" if result.score > 0 else "❌ FAIL"
        
        print(f"Status:           {status}")
        print(f"Score:            {score_pct:.1f}%")
        print(f"Queries Matched:  {result.n_covered}/{result.n_queries}")
        print(f"Pages Navigated:  {tracker.navigation_count}")
        print("-" * 80)
        
        for i, covered in enumerate(result.is_query_covered):
            status_icon = "✓" if covered else "✗"
            print(f"  Query {i+1}: [{status_icon}] {'Matched' if covered else 'Not matched'}")
        
        print("=" * 80 + "\n")
    
    @staticmethod
    def print_summary(results: list) -> None:
        """Print summary of all results."""
        if not results:
            return
        
        print("\n" + "=" * 80)
        print("SESSION SUMMARY")
        print("=" * 80)
        
        total = len(results)
        passed = sum(1 for r in results if r["score"] >= 1.0)
        
        print(f"Total Scenarios:  {total}")
        print(f"Passed:           {passed}")
        print(f"Success Rate:     {passed/total*100:.1f}%")
        print("=" * 80 + "\n")


# =============================================================================
# MAIN RUNNER
# =============================================================================

async def run_scenario(scenario: TaskScenario) -> dict:
    """Run a single verification scenario."""
    
    # Create evaluator
    task_config = generate_task_config_deterministic(
        mode="any",
        task=scenario.task_prompt,
        queries=scenario.queries,
        location=scenario.location,
        timezone=scenario.timezone,
        url=scenario.url,
    )
    
    evaluator = StubHubInfoGathering(queries=scenario.queries)
    tracker = NavigationTracker(evaluator, verbose=True)
    reporter = ResultReporter()
    
    # Display task info
    reporter.print_header(scenario)
    reporter.print_instructions()
    
    input("Press ENTER to launch browser...")
    
    async with async_playwright() as p:
        # Launch browser
        browser_mgr = BrowserManager()
        browser, context, page = await browser_mgr.launch(p)
        
        # Attach navigation tracking
        tracker.attach_to_context(context)
        await tracker.attach_to_page(page)
        
        # Navigate to start URL
        logger.info(f"Opening {scenario.url}")
        await page.goto(scenario.url, timeout=60000, wait_until="domcontentloaded")
        
        # Initialize evaluator
        await evaluator.reset()
        await evaluator.update(page=page)
        
        print("\n🌐 Browser ready - you are now the agent!")
        print("Navigate through StubHub to complete the task.\n")
        
        # Wait for user completion
        await asyncio.to_thread(
            input, 
            "Press ENTER when you've completed the task... "
        )
        
        # Final evaluation
        try:
            await evaluator.update(page=page)
        except Exception as e:
            logger.warning(f"Final update failed: {e}")
        
        result = await evaluator.compute()
        
        # Close browser
        await browser_mgr.close()
    
    # Display results
    reporter.print_result(result, tracker)
    
    return {
        "task_id": scenario.task_id,
        "score": result.score,
        "n_covered": result.n_covered,
        "n_queries": result.n_queries,
        "pages_navigated": tracker.navigation_count,
    }


async def run_interactive_menu() -> None:
    """Run interactive scenario selection menu."""
    
    print("\n" + "=" * 80)
    print("STUBHUB TICKET VERIFICATION SYSTEM")
    print("=" * 80)
    print("\nAvailable scenarios:\n")
    
    for i, scenario in enumerate(SCENARIOS, 1):
        print(f"  [{i}] {scenario.name}")
        print(f"      {scenario.description}")
        print()
    
    print(f"  [A] Run all scenarios")
    print(f"  [Q] Quit")
    print()
    
    choice = input("Select scenario (1-{}, A, or Q): ".format(len(SCENARIOS))).strip().upper()
    
    results = []
    
    if choice == "Q":
        print("Goodbye!")
        return
    
    elif choice == "A":
        for scenario in SCENARIOS:
            result = await run_scenario(scenario)
            results.append(result)
            
            if scenario != SCENARIOS[-1]:
                cont = input("\nContinue to next scenario? (y/n): ").strip().lower()
                if cont != "y":
                    break
    
    elif choice.isdigit() and 1 <= int(choice) <= len(SCENARIOS):
        idx = int(choice) - 1
        result = await run_scenario(SCENARIOS[idx])
        results.append(result)
    
    else:
        print("Invalid choice. Please try again.")
        return
    
    # Print summary
    ResultReporter.print_summary(results)


async def main():
    """Main entry point."""
    
    # Configure logging
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )
    
    try:
        await run_interactive_menu()
    except KeyboardInterrupt:
        print("\n\nInterrupted. Goodbye!")
    except Exception as e:
        logger.exception(f"Error: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
