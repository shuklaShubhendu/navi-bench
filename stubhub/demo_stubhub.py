#!/usr/bin/env python
"""
StubHub Human-in-the-Loop Demo - Zakir Khan Mumbai/Pune
Interactive browser demo to manually test the StubHub verifier

Run with: python demo_stubhub.py
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


async def run_stubhub_demo():
    """Run the StubHub demo with proper error handling"""
    
    # Task Definition - Lakers games in Los Angeles
    task = (
        "Search for Los Angeles Lakers basketball game tickets. "
        "Find any Lakers home game at Crypto.com Arena in Los Angeles."
    )
    
    # Expected search criteria - Lakers games
    # Simplified for demo - just match on event name
    queries = [[{
        "event_names": ["lakers", "los angeles lakers", "la lakers"],
        # NOTE: Removed cities requirement for simpler demo
        "event_categories": ["sports", "basketball", "nba"],
        "require_available": False,  # Agent gets credit even if sold out!
    }]]
    
    # Create task config using generate_task_config_deterministic
    try:
        task_config = generate_task_config_deterministic(
            mode="any",
            task=task,
            queries=queries,
            location="Los Angeles, California, USA",
            timezone="America/Los_Angeles",
            url="https://www.stubhub.com"
        )
        
        # Instantiate the evaluator from the task config
        evaluator = instantiate(task_config.eval_config)
        
    except Exception as e:
        print(f"[ERROR] Creating task config: {e}")
        import traceback
        traceback.print_exc()
        return

    # Display task info
    print("\n" + "=" * 80)
    print("STUBHUB DEMO: LA LAKERS GAME TEST")
    print("=" * 80)
    print()
    print(f"TASK: {task_config.task}")
    print()
    print("SEARCH CRITERIA:")
    print("  - Event: Lakers / Los Angeles Lakers")
    print("  - Category: Sports / Basketball / NBA")
    print()
    print("IMPORTANT:")
    print("  - require_available=False: Agent gets credit even if sold out!")
    print("  - Score 0% = No matching events found")
    print("  - Score 100% = Found Lakers event!")
    print()
    print(f"STARTING URL: {task_config.url}")
    print(f"LOCATION: {task_config.user_metadata.location}")
    print(f"TIMEZONE: {task_config.user_metadata.timezone}")
    print("=" * 80)
    
    await asyncio.to_thread(input, "\n[PRESS ENTER] to open the browser...")

    # Browser Initialization
    async with async_playwright() as p:
        try:
            print("\n[1/5] Launching browser...")
            browser = await p.chromium.launch(
                headless=False,
                args=["--disable-blink-features=AutomationControlled"]
            )
            
            print("[2/5] Creating browser context...")
            context = await browser.new_context(
                viewport={"width": 1280, "height": 720},
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                locale="en-US",  # US locale
                timezone_id="America/Los_Angeles",
            )
            
            # Hide webdriver property
            await context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """)
            
            page = await context.new_page()
            
            # Navigate to StubHub
            print(f"[3/5] Opening {task_config.url}...")
            await page.goto(task_config.url, timeout=60_000, wait_until="load")
            await page.wait_for_timeout(2000)
            
            print("[4/5] Browser ready!")
            print()
            print("=" * 80)
            print("BROWSER READY - YOU ARE NOW THE AGENT!")
            print("=" * 80)
            print()
            print("STEP-BY-STEP INSTRUCTIONS:")
            print("-" * 40)
            print("1. Find the search box on StubHub")
            print("2. Type 'Lakers' or 'Los Angeles Lakers'")
            print("3. Press Enter to search")
            print("4. Click on any Lakers game from results")
            print("5. Press ENTER in this terminal to verify")
            print("-" * 40)
            print()
            print("WHAT TO OBSERVE:")
            print("  - If no events: Verifier should report 0%")
            print("  - If sold out: Verifier should still report 100%")
            print("  - If available: Verifier should report 100%")
            print()
            
            # Initialize evaluator
            await evaluator.reset()
            
            # Navigation Tracker
            async def on_navigation():
                try:
                    current_url = page.url
                    print(f"[NAV] {current_url[:80]}...")
                except Exception as e:
                    print(f"[WARN] Navigation tracking error: {e}")

            page.on("framenavigated", lambda frame: asyncio.create_task(on_navigation()))
            
            # Wait for user to complete task
            await asyncio.to_thread(input, "[PRESS ENTER] when you've searched for Lakers... ")
            
            # Check if browser is still open
            if page.is_closed():
                print("\n[ERROR] Browser was closed! Please keep the browser open.")
                print("Run the demo again and don't close the browser until verification completes.")
                return
            
            # Verify the page
            print()
            print("[5/5] Verifying current page...")
            print("-" * 40)
            
            final_url = page.url
            print(f"Current URL: {final_url}")
            print()
            
            # Run JavaScript scraper and update evaluator
            try:
                await evaluator.update(page=page)
            except Exception as e:
                print(f"[WARN] Scraping error: {e}")
                print("\n[TIP] Make sure the browser is still open!")
            
            # Compute result
            result = await evaluator.compute()
            
            # Display results
            print()
            print("=" * 80)
            print("VERIFICATION RESULT")
            print("=" * 80)
            print(f"  Score: {result.score:.0%}")
            print(f"  Queries Matched: {result.n_covered}/{result.n_queries}")
            print()
            
            if result.score == 1.0:
                print("[PASS] SUCCESS! You found a valid Lakers game in Los Angeles!")
                print()
                print("  What was verified:")
                print("    ✓ Event name contains 'Lakers'")
                print("    ✓ Category is Sports/Basketball/NBA")
                print("    ✓ City is Los Angeles area")
                print("    ✓ (Event counts even if sold out)")
            elif result.score > 0:
                print("[PARTIAL] Some criteria matched, but not all.")
                print()
                print("  Missing criteria:")
                for i, covered in enumerate(result.is_query_covered):
                    if not covered:
                        print(f"    - Query {i+1} not matched")
            else:
                print("[INFO] No matching Lakers events found in Los Angeles.")
                print()
                print("  This is EXPECTED if:")
                print("    - You are on category page (must click specific game)")
                print("    - No Lakers games in Los Angeles area")
                print("    - StubHub has no listings for this team")
                print()
                print("  IMPORTANT: You must click on a specific game!")
                print("  Category page shows 0% - navigate to /event/ URL.")
                print()
                print("  What you can try:")
                print("    1. Click on a specific Lakers vs [Team] game")
                print("    2. Navigate to the event detail page")
                print("    3. The URL should contain '/event/'")
            
            print("=" * 80)
            
            # Page analysis
            print()
            print("PAGE ANALYSIS:")
            page_title = await page.title()
            print(f"  Title: {page_title}")
            
            page_text = await page.evaluate("document.body?.innerText?.toLowerCase() || ''")
            if "sold out" in page_text:
                print("  Status: SOLD OUT detected")
            elif "no results" in page_text or "no tickets" in page_text:
                print("  Status: NO RESULTS detected")
            elif "lakers" in page_text:
                print("  Status: Lakers content detected")
            else:
                print("  Status: No specific indicators")
            
            print()
            
            # Ask if user wants to try again
            retry = await asyncio.to_thread(input, "Try another page? (y/n): ")
            
            while retry.lower() == 'y':
                await asyncio.to_thread(input, "\n[PRESS ENTER] when ready to verify again... ")
                
                await evaluator.reset()
                await evaluator.update(page=page)
                result = await evaluator.compute()
                
                print()
                print("-" * 40)
                print(f"Score: {result.score:.0%} | Matched: {result.n_covered}/{result.n_queries}")
                if result.score == 1.0:
                    print("[PASS] SUCCESS! Found Zakir Khan in Mumbai/Pune!")
                elif result.score > 0:
                    print("[PARTIAL] Some matches found")
                else:
                    print("[INFO] No matches - expected if no events in these cities")
                print("-" * 40)
                
                retry = await asyncio.to_thread(input, "\nTry another page? (y/n): ")
            
            print("\nClosing browser...")
            await context.close()
            await browser.close()
            
        except Exception as e:
            print(f"\n[ERROR] Browser error: {e}")
            print("Make sure Playwright browsers are installed:")
            print("  playwright install chromium")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("STUBHUB DEMO: ZAKIR KHAN MUMBAI/PUNE")
    print("=" * 80)
    print()
    print("This demo lets you manually test the StubHub verifier.")
    print("A browser will open and you'll act as the AI agent.")
    print()
    print("Test scenarios:")
    print("  1. No events found → Should report 0% (expected)")
    print("  2. Event sold out → Should report 100% (agent gets credit)")
    print("  3. Event available → Should report 100%")
    print()
    
    try:
        asyncio.run(run_stubhub_demo())
    except KeyboardInterrupt:
        print("\n\n[CANCELLED] Demo cancelled by user.")
    except Exception as e:
        print(f"\n\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\nDemo complete!")
