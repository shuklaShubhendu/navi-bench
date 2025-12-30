#!/usr/bin/env python
"""
StubHub Automated Verification Agent

Automated browser agent that demonstrates the StubHub verification system
without manual intervention. Performs searches, navigates to events, and
validates the verification process end-to-end.

Features:
- Fully automated search and navigation
- Multi-tab support with real-time tracking
- Stealth browser configuration
- Comprehensive result reporting

Usage:
    python auto_demo_stubhub.py
"""

import asyncio
import sys
from dataclasses import dataclass, field
from typing import Optional

from playwright.async_api import Page, BrowserContext, async_playwright
from loguru import logger

# Import verifier
from navi_bench.stubhub.stubhub_info_gathering import (
    StubHubInfoGathering,
    generate_task_config_deterministic,
)


# =============================================================================
# CONFIGURATION
# =============================================================================

@dataclass
class AutomationConfig:
    """Configuration for automated verification runs."""
    search_term: str = "NBA"
    max_navigation_steps: int = 5
    wait_between_actions_ms: int = 2000
    screenshot_on_complete: bool = False
    headless: bool = False
    

@dataclass
class BrowserConfig:
    """Browser launch configuration."""
    viewport_width: int = 1366
    viewport_height: int = 768
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    locale: str = "en-US"
    timezone: str = "America/New_York"
    launch_args: list = field(default_factory=lambda: [
        "--disable-blink-features=AutomationControlled",
        "--disable-infobars",
        "--no-sandbox",
    ])


# =============================================================================
# NAVIGATION TRACKER
# =============================================================================

class NavigationTracker:
    """Tracks navigation events and updates evaluator in real-time."""
    
    def __init__(self, evaluator: StubHubInfoGathering):
        self.evaluator = evaluator
        self.navigation_count = 0
        self.pages_tracked: set[int] = set()
        self._lock = asyncio.Lock()
    
    async def attach_to_page(self, page: Page) -> None:
        """Attach tracking to a page."""
        page_id = id(page)
        if page_id in self.pages_tracked:
            return
        self.pages_tracked.add(page_id)
        
        async def on_navigate(frame):
            if frame != page.main_frame:
                return
            async with self._lock:
                self.navigation_count += 1
                logger.info(f"[NAV #{self.navigation_count}] {page.url[:70]}...")
                try:
                    await self.evaluator.update(page=page)
                except Exception as e:
                    logger.debug(f"Update error: {e}")
        
        page.on("framenavigated", lambda f: asyncio.create_task(on_navigate(f)))
    
    async def handle_new_page(self, new_page: Page) -> None:
        """Handle new tab/popup."""
        try:
            await new_page.wait_for_load_state("domcontentloaded", timeout=10000)
            logger.info(f"[NEW TAB] {new_page.url[:60]}...")
            await self.attach_to_page(new_page)
            await self.evaluator.update(page=new_page)
        except Exception as e:
            logger.debug(f"New tab error: {e}")
    
    def attach_to_context(self, context: BrowserContext) -> None:
        """Attach to browser context for new page detection."""
        context.on("page", lambda p: asyncio.create_task(self.handle_new_page(p)))


# =============================================================================
# AUTOMATED AGENT
# =============================================================================

class AutomatedAgent:
    """Automated agent that navigates StubHub and triggers verification."""
    
    def __init__(self, page: Page, config: AutomationConfig):
        self.page = page
        self.config = config
        self.actions_taken = []
    
    async def _wait(self, multiplier: float = 1.0) -> None:
        """Wait between actions."""
        await asyncio.sleep(self.config.wait_between_actions_ms * multiplier / 1000)
    
    async def search_for_event(self, search_term: str) -> bool:
        """Search for an event on StubHub."""
        logger.info(f"Searching for: {search_term}")
        
        try:
            # Look for search input
            search_selectors = [
                'input[placeholder*="Search"]',
                'input[type="search"]',
                'input[data-testid*="search"]',
                'input[aria-label*="Search"]',
                '#search-input',
            ]
            
            for selector in search_selectors:
                try:
                    search_box = await self.page.wait_for_selector(selector, timeout=3000)
                    if search_box:
                        await search_box.click()
                        await self._wait(0.5)
                        await search_box.fill(search_term)
                        await self._wait(0.5)
                        await self.page.keyboard.press("Enter")
                        self.actions_taken.append(f"Searched: {search_term}")
                        logger.info("Search submitted")
                        return True
                except Exception:
                    continue
            
            logger.warning("Could not find search box")
            return False
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return False
    
    async def click_first_event(self) -> bool:
        """Click on the first event in search results."""
        logger.info("Looking for events to click...")
        
        try:
            await self._wait(2)  # Wait for results
            
            # Event link selectors
            event_selectors = [
                'a[href*="/event/"]',
                '[data-testid*="event"] a',
                '.event-listing a',
                '[class*="EventRow"] a',
            ]
            
            for selector in event_selectors:
                try:
                    events = await self.page.query_selector_all(selector)
                    if events and len(events) > 0:
                        await events[0].click()
                        self.actions_taken.append("Clicked first event")
                        logger.info("Clicked on event")
                        return True
                except Exception:
                    continue
            
            logger.warning("No events found to click")
            return False
            
        except Exception as e:
            logger.error(f"Click failed: {e}")
            return False
    
    async def run_automation(self) -> list:
        """Run the automated navigation sequence."""
        steps = [
            ("Search for events", lambda: self.search_for_event(self.config.search_term)),
            ("Wait for results", lambda: self._wait(2)),
            ("Click first event", self.click_first_event),
            ("Wait for event page", lambda: self._wait(2)),
        ]
        
        for step_name, step_func in steps:
            logger.info(f"Step: {step_name}")
            try:
                result = await step_func()
                if result is False:
                    logger.warning(f"Step '{step_name}' did not complete as expected")
            except Exception as e:
                logger.error(f"Step '{step_name}' failed: {e}")
        
        return self.actions_taken


# =============================================================================
# MAIN RUNNER
# =============================================================================

async def run_automated_demo():
    """Run the automated StubHub demonstration."""
    
    print("\n" + "=" * 80)
    print("STUBHUB AUTOMATED VERIFICATION DEMO")
    print("=" * 80)
    print("\nThis demo automatically:")
    print("  1. Opens StubHub")
    print("  2. Searches for events")
    print("  3. Navigates to event pages")
    print("  4. Verifies the page content")
    print("\n" + "=" * 80)
    
    # Configuration
    auto_config = AutomationConfig(
        search_term="NBA",
        wait_between_actions_ms=2000,
    )
    browser_config = BrowserConfig()
    
    # Create evaluator
    queries = [[{
        "event_names": ["nba", "basketball"],
        "event_categories": ["sports"],
        "require_available": False,
    }]]
    
    evaluator = StubHubInfoGathering(queries=queries)
    tracker = NavigationTracker(evaluator)
    
    print(f"\nSearch Term: {auto_config.search_term}")
    print("=" * 80)
    
    async with async_playwright() as p:
        # Launch browser
        logger.info("Launching browser...")
        browser = await p.chromium.launch(
            headless=auto_config.headless,
            args=browser_config.launch_args,
        )
        
        context = await browser.new_context(
            viewport={"width": browser_config.viewport_width, "height": browser_config.viewport_height},
            user_agent=browser_config.user_agent,
            locale=browser_config.locale,
            timezone_id=browser_config.timezone,
        )
        
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            window.chrome = { runtime: {} };
        """)
        
        page = await context.new_page()
        
        # Attach tracking
        tracker.attach_to_context(context)
        await tracker.attach_to_page(page)
        
        # Navigate to StubHub
        logger.info("Opening StubHub...")
        await page.goto("https://www.stubhub.com", timeout=60000, wait_until="domcontentloaded")
        
        await evaluator.reset()
        await evaluator.update(page=page)
        
        # Run automation
        logger.info("Starting automated navigation...")
        agent = AutomatedAgent(page, auto_config)
        actions = await agent.run_automation()
        
        # Final evaluation
        logger.info("Running final evaluation...")
        await evaluator.update(page=page)
        result = await evaluator.compute()
        
        # Close browser
        await context.close()
        await browser.close()
    
    # Print results
    print("\n" + "=" * 80)
    print("VERIFICATION RESULT")
    print("=" * 80)
    
    score_pct = result.score * 100
    status = "✅ PASS" if result.score >= 1.0 else "⚠️ PARTIAL" if result.score > 0 else "❌ FAIL"
    
    print(f"Status:           {status}")
    print(f"Score:            {score_pct:.1f}%")
    print(f"Queries Matched:  {result.n_covered}/{result.n_queries}")
    print(f"Pages Navigated:  {tracker.navigation_count}")
    print(f"Actions Taken:    {len(actions)}")
    print("-" * 80)
    
    for i, covered in enumerate(result.is_query_covered):
        icon = "✓" if covered else "✗"
        print(f"  Query {i+1}: [{icon}] {'Matched' if covered else 'Not matched'}")
    
    print("=" * 80)
    print("\nAutomation complete!")
    
    return result


async def main():
    """Main entry point."""
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )
    
    try:
        await run_automated_demo()
    except KeyboardInterrupt:
        print("\nInterrupted.")
    except Exception as e:
        logger.exception(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
