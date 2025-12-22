#!/usr/bin/env python
"""
StubHub Human-in-the-Loop Demo
Interactive browser demo to test the StubHub verifier manually
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
    
    # Create task config using generate_task_config_deterministic
    try:
        task_config = generate_task_config_deterministic(
            mode="any",
            task=task,
            queries=queries,
            location="Los Angeles, CA, United States",
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
    print("STUBHUB HUMAN-IN-THE-LOOP DEMO")
    print("=" * 80)
    print()
    print(f"TASK: {task_config.task}")
    print()
    print("SEARCH CRITERIA:")
    print("  - Event: Lakers / Los Angeles Lakers / LA Lakers")
    print("  - City: Los Angeles / Inglewood / LA")
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
            
            print("[2/5] Creating browser context with anti-detection...")
            context = await browser.new_context(
                viewport={"width": 1280, "height": 720},
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                locale="en-US",
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
            print("2. Type 'Lakers' and press Enter")
            print("3. Click on any Lakers game from the results")
            print("4. Navigate to a page showing ticket listings")
            print("5. Press ENTER in this terminal to verify")
            print("-" * 40)
            print()
            print("EXPECTED RESULT URL (example):")
            print("  https://www.stubhub.com/los-angeles-lakers-los-angeles-tickets-.../event/...")
            print()
            print("WHAT THE VERIFIER CHECKS:")
            print("  - Event name contains 'lakers'")
            print("  - City is Los Angeles or Inglewood")
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
            await asyncio.to_thread(input, "[PRESS ENTER] when you've found a Lakers event page... ")
            
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
                print("[PASS] SUCCESS! You found a valid Lakers event!")
                print()
                print("The page shows:")
                print("  - Event name matching 'Lakers'")
                print("  - Location in Los Angeles area")
            elif result.score > 0:
                print("[PARTIAL] Some criteria matched, but not all.")
                print()
                print("Missing criteria:")
                for i, covered in enumerate(result.is_query_covered):
                    if not covered:
                        print(f"  - Query {i+1} not matched")
            else:
                print("[FAIL] No matching events found on this page.")
                print()
                print("Possible reasons:")
                print("  - You're not on an event page")
                print("  - The event is not a Lakers game")
                print("  - The page structure couldn't be parsed")
                print()
                print("Try:")
                print("  1. Search for 'Lakers' in the StubHub search")
                print("  2. Click on a specific Lakers game")
                print("  3. Make sure you see ticket listings")
            
            print("=" * 80)
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
                    print("[PASS] SUCCESS!")
                else:
                    print("[FAIL] Not matched")
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
    print("STUBHUB HUMAN-IN-THE-LOOP DEMO")
    print("=" * 80)
    print()
    print("This demo lets you manually test the StubHub verifier.")
    print("A browser will open and you'll act as the AI agent.")
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
