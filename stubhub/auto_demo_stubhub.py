#!/usr/bin/env python
"""
StubHub Automated Demo Agent - Zakir Khan Mumbai/Pune Test
Tests the verifier behavior when no tickets are found.

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


async def run_zakir_khan_demo():
    """Search for Zakir Khan in Mumbai/Pune to test no-ticket scenarios"""
    
    print("\n" + "=" * 80)
    print("STUBHUB DEMO: ZAKIR KHAN MUMBAI/PUNE TEST")
    print("=" * 80)
    print()
    print("This test searches for Zakir Khan tickets in Mumbai/Pune to verify")
    print("how the system handles scenarios where:")
    print("  - No tickets are available")
    print("  - Event is sold out")
    print("  - No events found in that region")
    print()
    
    # Task Definition
    task = (
        "Search for Zakir Khan comedy show tickets in Mumbai or Pune, India. "
        "Find any Zakir Khan stand-up event available in these cities."
    )
    
    # Expected search criteria - Mumbai/Pune specific
    # NOTE: require_available=False means agent gets credit even for sold-out events
    queries = [[{
        "event_names": ["zakir khan", "zakir", "haq se single", "kaksha gyarvi", "tathastu"],
        "event_categories": ["comedy", "standup", "stand-up"],
        # Mumbai/Pune specific
        "cities": ["mumbai", "pune", "navi mumbai", "thane"],
        "require_available": False  # Credit even if sold out!
    }]]
    
    # Create task config
    try:
        task_config = generate_task_config_deterministic(
            mode="any",
            task=task,
            queries=queries,
            location="Mumbai, Maharashtra, India",
            timezone="Asia/Kolkata",
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
            print("[1/7] Launching browser...")
            browser = await p.chromium.launch(
                headless=False,  # Show the browser
                args=["--disable-blink-features=AutomationControlled"]
            )
            
            context = await browser.new_context(
                viewport={"width": 1280, "height": 720},
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                locale="en-IN",  # India locale
                timezone_id="Asia/Kolkata",
            )
            
            await context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """)
            
            page = await context.new_page()
            
            # Step 1: Navigate to StubHub
            print("[2/7] Opening StubHub.com...")
            await page.goto("https://www.stubhub.com", timeout=60_000, wait_until="load")
            await page.wait_for_timeout(3000)
            print(f"       Current URL: {page.url}")
            
            # Step 2: Search for Zakir Khan Mumbai
            print("[3/7] Searching for 'Zakir Khan Mumbai'...")
            
            search_selectors = [
                'input[type="search"]',
                'input[placeholder*="Search"]',
                'input[aria-label*="Search"]',
                'input[name="q"]',
                '#search-input',
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
            
            search_query = "Zakir Khan Mumbai"
            
            if search_box:
                await search_box.click()
                await page.wait_for_timeout(500)
                await search_box.fill(search_query)
                await page.wait_for_timeout(500)
                await search_box.press("Enter")
                await page.wait_for_timeout(5000)
                print(f"       Search submitted. URL: {page.url[:80]}...")
            else:
                print("[WARN] Could not find search box. Trying direct URL...")
                await page.goto("https://www.stubhub.com/secure/Search?q=Zakir+Khan+Mumbai", timeout=60_000)
                await page.wait_for_timeout(5000)
            
            # Step 3: First verification on search results page
            print("[4/7] Verifying search results page...")
            print("-" * 40)
            
            await evaluator.reset()
            await evaluator.update(page=page)
            search_result = await evaluator.compute()
            
            print(f"       Search page score: {search_result.score:.0%}")
            print(f"       Queries matched: {search_result.n_covered}/{search_result.n_queries}")
            print()
            
            # Step 4: Try to click on a Zakir Khan event
            print("[5/7] Looking for Zakir Khan event links...")
            
            event_selectors = [
                'a[href*="zakir"][href*="event"]',
                'a[href*="zakir-khan"]',
                'a[href*="/event/"]',
            ]
            
            event_clicked = False
            for selector in event_selectors:
                try:
                    links = await page.query_selector_all(selector)
                    for link in links:
                        href = await link.get_attribute("href") or ""
                        text = await link.text_content() or ""
                        if "zakir" in href.lower() or "zakir" in text.lower():
                            print(f"       Found event: {text[:50]}...")
                            print(f"       URL: {href[:60]}...")
                            await link.click()
                            event_clicked = True
                            await page.wait_for_timeout(5000)
                            break
                    if event_clicked:
                        break
                except:
                    continue
            
            if not event_clicked:
                print("[INFO] No Zakir Khan events found directly.")
                print("       This is expected if there are no Mumbai/Pune events.")
            
            print(f"       Current URL: {page.url}")
            
            # Step 5: Verify the final page
            print("[6/7] Running final verification...")
            print("-" * 40)
            
            await evaluator.reset()
            await evaluator.update(page=page)
            final_result = await evaluator.compute()
            
            # Step 6: Display comprehensive results
            print()
            print("=" * 80)
            print("VERIFICATION RESULT")
            print("=" * 80)
            print()
            print(f"  Final URL: {page.url}")
            print()
            print(f"  Score: {final_result.score:.0%}")
            print(f"  Queries Matched: {final_result.n_covered}/{final_result.n_queries}")
            print()
            
            if final_result.score == 1.0:
                print("[PASS] SUCCESS! Found a valid Zakir Khan event in Mumbai/Pune!")
                print()
                print("  What was verified:")
                print("    ✓ Event name contains 'Zakir Khan'")
                print("    ✓ Category is Comedy/Standup")
                print("    ✓ City is Mumbai or Pune")
                print("    ✓ (Event counts even if sold out)")
            elif final_result.score > 0:
                print("[PARTIAL] Found partial match for Zakir Khan.")
                print()
                print("  The agent found some matching content but not all criteria.")
            else:
                print("[INFO] No Zakir Khan events found in Mumbai/Pune.")
                print()
                print("  This is the expected result if:")
                print("    - No Zakir Khan shows are listed in these cities")
                print("    - All events are in other locations")
                print("    - StubHub doesn't have listings for this artist/region")
                print()
                print("  KEY INSIGHT: The verifier correctly reports 0% when no")
                print("  matching events exist. This is NOT a bug - it's the")
                print("  expected behavior for the 'no tickets available' case.")
                
            print()
            print("=" * 80)
            print("PAGE ANALYSIS")
            print("=" * 80)
            
            # Show what the scraper found
            page_title = await page.title()
            print(f"  Page Title: {page_title}")
            
            # Check for sold out / no results indicators
            page_text = await page.evaluate("document.body?.innerText || ''")
            page_text_lower = page_text.lower()
            
            if "sold out" in page_text_lower:
                print("  Status: SOLD OUT detected on page")
            elif "no results" in page_text_lower or "no tickets" in page_text_lower:
                print("  Status: NO RESULTS detected on page")
            elif "zakir" in page_text_lower:
                print("  Status: Zakir Khan content detected on page")
            else:
                print("  Status: No specific status indicators found")
            
            print("=" * 80)
            
            # Keep browser open for viewing
            print()
            print("[7/7] Demo complete! Browser will close in 10 seconds...")
            print("      (You can examine the page)")
            await page.wait_for_timeout(10000)
            
            await context.close()
            await browser.close()
            
        except Exception as e:
            print(f"\n[ERROR] {e}")
            import traceback
            traceback.print_exc()


async def run_pune_search():
    """Also try Pune specifically"""
    print("\n" + "=" * 80)
    print("ADDITIONAL TEST: Searching Pune specifically...")
    print("=" * 80)
    
    # This is a simpler version just to check Pune
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(viewport={"width": 1280, "height": 720})
        page = await context.new_page()
        
        await page.goto("https://www.stubhub.com")
        await page.wait_for_timeout(2000)
        
        try:
            search = await page.wait_for_selector('input[type="search"], input[placeholder*="Search"]', timeout=10000)
            if search:
                await search.fill("Zakir Khan Pune")
                await search.press("Enter")
                await page.wait_for_timeout(5000)
                print(f"  Pune search URL: {page.url}")
        except:
            pass
        
        await page.wait_for_timeout(5000)
        await browser.close()


if __name__ == "__main__":
    print()
    print("=" * 80)
    print("STUBHUB VERIFIER TEST: ZAKIR KHAN MUMBAI/PUNE")
    print("=" * 80)
    print()
    print("This test demonstrates how the verifier handles:")
    print("  1. Events that exist but are sold out")
    print("  2. No events found for the search")
    print("  3. Events in different cities than requested")
    print()
    print("Watch the browser - the agent will search automatically!")
    print()
    
    try:
        asyncio.run(run_zakir_khan_demo())
    except KeyboardInterrupt:
        print("\n\n[CANCELLED] Demo cancelled by user.")
    except Exception as e:
        print(f"\n\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
    
    print("\nDemo complete!")
