#!/usr/bin/env python
"""
StubHub Automated Demo Agent
Automatically performs the search and verification - no human interaction needed.

Run with: python auto_demo_stubhub.py
"""

import asyncio
from playwright.async_api import async_playwright

# Import the StubHub verifier
try:
    from navi_bench.stubhub.stubhub_info_gathering import (
        StubHubInfoGathering,
        generate_task_config_deterministic,
    )
    from navi_bench.base import instantiate
except ImportError as e:
    print(f"[ERROR] Could not import navi_bench modules: {e}")
    print("Make sure you're running from the navi-bench directory and it's installed.")
    print("Run: python -m pip install -e .")
    exit(1)


async def run_automated_demo():
    """Automated demo - the bot does everything automatically"""
    
    print("\n" + "=" * 80)
    print("STUBHUB AUTOMATED DEMO AGENT")
    print("=" * 80)
    print()
    print("This agent will automatically:")
    print("  1. Open StubHub")
    print("  2. Search for 'Lakers'")
    print("  3. Click on a Lakers event")
    print("  4. Verify the page")
    print()
    
    # Task Definition
    task = (
        "Search for Lakers tickets in Los Angeles. "
        "Find any Lakers game with available tickets."
    )
    
    # Expected search criteria
    queries = [[{
        "event_names": ["lakers", "los angeles lakers", "la lakers"],
        "cities": ["los angeles", "inglewood", "la"]
    }]]
    
    # Create task config
    try:
        task_config = generate_task_config_deterministic(
            mode="any",
            task=task,
            queries=queries,
            location="Los Angeles, CA, United States",
            timezone="America/Los_Angeles",
            url="https://www.stubhub.com"
        )
        evaluator = instantiate(task_config.eval_config)
    except Exception as e:
        print(f"[ERROR] Creating task config: {e}")
        return

    print(f"TASK: {task}")
    print("=" * 80)
    print()

    async with async_playwright() as p:
        try:
            # Launch browser
            print("[1/6] Launching browser...")
            browser = await p.chromium.launch(
                headless=False,  # Show the browser
                args=["--disable-blink-features=AutomationControlled"]
            )
            
            context = await browser.new_context(
                viewport={"width": 1280, "height": 720},
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                locale="en-US",
                timezone_id="America/Los_Angeles",
            )
            
            await context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """)
            
            page = await context.new_page()
            
            # Step 1: Navigate to StubHub
            print("[2/6] Opening StubHub.com...")
            await page.goto("https://www.stubhub.com", timeout=60_000, wait_until="load")
            await page.wait_for_timeout(3000)
            print(f"       Current URL: {page.url}")
            
            # Step 2: Search for Lakers
            print("[3/6] Searching for 'Lakers'...")
            
            # Try multiple search box selectors
            search_selectors = [
                'input[type="search"]',
                'input[placeholder*="Search"]',
                'input[aria-label*="Search"]',
                'input[name="q"]',
                '#search-input',
                '[data-testid="search-input"]'
            ]
            
            search_box = None
            for selector in search_selectors:
                try:
                    search_box = await page.wait_for_selector(selector, timeout=5000)
                    if search_box:
                        print(f"       Found search box: {selector}")
                        break
                except:
                    continue
            
            if search_box:
                await search_box.click()
                await page.wait_for_timeout(500)
                await search_box.fill("Lakers")
                await page.wait_for_timeout(500)
                await search_box.press("Enter")
                await page.wait_for_timeout(5000)
                print(f"       Search submitted. URL: {page.url[:80]}...")
            else:
                print("[WARN] Could not find search box. Trying direct URL...")
                await page.goto("https://www.stubhub.com/secure/Search?q=lakers", timeout=60_000)
                await page.wait_for_timeout(5000)
            
            # Step 3: Click on first Lakers event
            print("[4/6] Looking for Lakers event links...")
            
            event_selectors = [
                'a[href*="lakers"][href*="event"]',
                'a[href*="los-angeles-lakers"]',
                'a[href*="/event/"]',
                '[class*="EventItem"] a',
                '[class*="event"] a'
            ]
            
            event_clicked = False
            for selector in event_selectors:
                try:
                    links = await page.query_selector_all(selector)
                    for link in links:
                        href = await link.get_attribute("href") or ""
                        if "lakers" in href.lower():
                            print(f"       Found Lakers event link: {href[:60]}...")
                            await link.click()
                            event_clicked = True
                            await page.wait_for_timeout(5000)
                            break
                    if event_clicked:
                        break
                except:
                    continue
            
            if not event_clicked:
                print("[WARN] Could not click event link. Trying to find any event...")
                # Try clicking any visible event link
                try:
                    first_event = await page.query_selector('a[href*="/event/"]')
                    if first_event:
                        await first_event.click()
                        await page.wait_for_timeout(5000)
                except:
                    pass
            
            print(f"       Current URL: {page.url}")
            
            # Step 4: Verify the page
            print("[5/6] Running verifier on current page...")
            print("-" * 40)
            
            await evaluator.reset()
            await evaluator.update(page=page)
            result = await evaluator.compute()
            
            # Step 5: Display results
            print()
            print("=" * 80)
            print("VERIFICATION RESULT")
            print("=" * 80)
            print(f"  Final URL: {page.url}")
            print()
            print(f"  Score: {result.score:.0%}")
            print(f"  Queries Matched: {result.n_covered}/{result.n_queries}")
            print()
            
            if result.score == 1.0:
                print("[PASS] SUCCESS! The agent found a valid Lakers event!")
                print()
                print("  Criteria matched:")
                print("    - Event name: Lakers")
                print("    - City: Los Angeles area")
            else:
                print("[FAIL] The agent could not verify the event.")
                print()
                print("  Possible issues:")
                print("    - Bot detection blocked the page")
                print("    - Page structure changed")
                print("    - No Lakers events found")
                
                # Show page content for debugging
                print()
                print("  Page title:", await page.title())
                
            print("=" * 80)
            
            # Keep browser open for a moment so user can see
            print()
            print("[6/6] Demo complete! Browser will close in 5 seconds...")
            await page.wait_for_timeout(5000)
            
            await context.close()
            await browser.close()
            
        except Exception as e:
            print(f"\n[ERROR] {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    print()
    print("=" * 80)
    print("STUBHUB AUTOMATED DEMO")
    print("=" * 80)
    print()
    print("Watch the browser - the agent will do everything automatically!")
    print()
    
    try:
        asyncio.run(run_automated_demo())
    except KeyboardInterrupt:
        print("\n\n[CANCELLED] Demo cancelled by user.")
    except Exception as e:
        print(f"\n\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
    
    print("\nDemo complete!")
