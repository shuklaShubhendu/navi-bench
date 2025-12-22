#!/usr/bin/env python
"""
StubHub Batch Demo Runner
Run multiple demo tests and see pass/fail results.

Usage:
    python batch_demo_stubhub.py              # Run all 5 default tests
    python batch_demo_stubhub.py --count 3    # Run 3 tests
    python batch_demo_stubhub.py --headless   # Run without visible browser
"""

import asyncio
import argparse
from datetime import datetime, timedelta
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
    print("Run: python -m pip install -e .")
    exit(1)


# ============================================================================
# TEST CASES - Add more test cases here
# ============================================================================

TEST_CASES = [
    {
        "name": "Lakers Search",
        "search_term": "Lakers",
        "queries": [[{
            "event_names": ["lakers", "los angeles lakers", "la lakers"],
            "cities": ["los angeles", "inglewood", "la"]
        }]],
        "description": "Search for any Lakers game in LA"
    },
    {
        "name": "Warriors Search",
        "search_term": "Warriors",
        "queries": [[{
            "event_names": ["warriors", "golden state warriors", "gsw"],
            "cities": ["san francisco", "sf", "oakland"]
        }]],
        "description": "Search for Warriors game in SF Bay Area"
    },
    {
        "name": "Taylor Swift Concert",
        "search_term": "Taylor Swift",
        "queries": [[{
            "event_names": ["taylor swift", "eras tour", "swift"],
        }]],
        "description": "Search for Taylor Swift concert"
    },
    {
        "name": "NBA Generic",
        "search_term": "NBA",
        "queries": [[{
            "event_names": ["nba", "basketball", "lakers", "warriors", "celtics", "heat"],
        }]],
        "description": "Search for any NBA game"
    },
    {
        "name": "Clippers Search",
        "search_term": "Clippers",
        "queries": [[{
            "event_names": ["clippers", "la clippers", "los angeles clippers"],
            "cities": ["los angeles", "inglewood", "la"]
        }]],
        "description": "Search for Clippers game in LA"
    },
    {
        "name": "Concert Generic",
        "search_term": "Concert Los Angeles",
        "queries": [[{
            "event_names": ["concert", "live", "tour"],
            "cities": ["los angeles", "la", "hollywood"]
        }]],
        "description": "Search for any concert in LA"
    },
    {
        "name": "Hamilton Broadway",
        "search_term": "Hamilton",
        "queries": [[{
            "event_names": ["hamilton", "broadway"],
        }]],
        "description": "Search for Hamilton tickets"
    },
    {
        "name": "Dodgers Baseball",
        "search_term": "Dodgers",
        "queries": [[{
            "event_names": ["dodgers", "los angeles dodgers", "la dodgers"],
            "cities": ["los angeles", "la"]
        }]],
        "description": "Search for Dodgers baseball game"
    },
]


async def run_single_test(test_case: dict, browser, headless: bool = False) -> dict:
    """Run a single test case and return result."""
    
    result = {
        "name": test_case["name"],
        "description": test_case["description"],
        "search_term": test_case["search_term"],
        "passed": False,
        "score": 0.0,
        "events_found": 0,
        "error": None
    }
    
    try:
        # Create evaluator
        evaluator = StubHubInfoGathering(queries=test_case["queries"])
        
        # Create context
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
        
        # Navigate and search
        await page.goto("https://www.stubhub.com", timeout=60_000, wait_until="load")
        await page.wait_for_timeout(2000)
        
        # Find and use search box
        search_box = None
        for selector in ['input[placeholder*="Search"]', 'input[type="search"]', 'input[aria-label*="Search"]']:
            try:
                search_box = await page.wait_for_selector(selector, timeout=3000)
                if search_box:
                    break
            except:
                continue
        
        if search_box:
            await search_box.click()
            await page.wait_for_timeout(300)
            await search_box.fill(test_case["search_term"])
            await page.wait_for_timeout(300)
            await search_box.press("Enter")
            await page.wait_for_timeout(4000)
        else:
            # Fallback to direct URL
            encoded_search = test_case["search_term"].replace(" ", "+")
            await page.goto(f"https://www.stubhub.com/secure/Search?q={encoded_search}", timeout=60_000)
            await page.wait_for_timeout(3000)
        
        # Run verifier
        await evaluator.reset()
        await evaluator.update(page=page)
        compute_result = await evaluator.compute()
        
        result["score"] = compute_result.score
        result["passed"] = compute_result.score >= 1.0
        result["events_found"] = compute_result.n_covered
        
        await context.close()
        
    except Exception as e:
        result["error"] = str(e)
    
    return result


async def run_batch_demo(count: int = 5, headless: bool = False):
    """Run multiple demo tests."""
    
    print("\n" + "=" * 80)
    print("STUBHUB BATCH DEMO RUNNER")
    print("=" * 80)
    print(f"\nTests to run: {count}")
    print(f"Headless mode: {headless}")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    # Limit to available test cases
    tests_to_run = TEST_CASES[:min(count, len(TEST_CASES))]
    
    results = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=headless,
            args=["--disable-blink-features=AutomationControlled"]
        )
        
        for i, test_case in enumerate(tests_to_run, 1):
            print(f"\n[Test {i}/{len(tests_to_run)}] {test_case['name']}")
            print(f"  Searching: '{test_case['search_term']}'")
            print(f"  Description: {test_case['description']}")
            
            result = await run_single_test(test_case, browser, headless)
            results.append(result)
            
            if result["error"]:
                print(f"  Result: [ERROR] {result['error'][:50]}...")
            elif result["passed"]:
                print(f"  Result: [PASS] Score: {result['score']:.0%}")
            else:
                print(f"  Result: [FAIL] Score: {result['score']:.0%}")
            
            # Small delay between tests
            await asyncio.sleep(1)
        
        await browser.close()
    
    # Summary
    print("\n" + "=" * 80)
    print("BATCH DEMO RESULTS SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for r in results if r["passed"])
    failed = sum(1 for r in results if not r["passed"] and not r["error"])
    errors = sum(1 for r in results if r["error"])
    
    print(f"\nTotal Tests: {len(results)}")
    print(f"  [PASS]: {passed}")
    print(f"  [FAIL]: {failed}")
    print(f"  [ERROR]: {errors}")
    print(f"\nPass Rate: {passed/len(results)*100:.1f}%")
    
    print("\n" + "-" * 80)
    print("DETAILED RESULTS:")
    print("-" * 80)
    
    for r in results:
        status = "[PASS]" if r["passed"] else ("[ERROR]" if r["error"] else "[FAIL]")
        print(f"  {status:8} {r['name']:25} - Score: {r['score']:.0%} | {r['description'][:40]}")
    
    print("\n" + "=" * 80)
    print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="StubHub Batch Demo Runner")
    parser.add_argument("--count", "-c", type=int, default=5, help="Number of tests to run (default: 5)")
    parser.add_argument("--headless", "-hl", action="store_true", help="Run in headless mode")
    args = parser.parse_args()
    
    print("\n" + "=" * 80)
    print("STUBHUB BATCH DEMO")
    print("=" * 80)
    print(f"\nAvailable test cases: {len(TEST_CASES)}")
    print(f"Tests requested: {args.count}")
    print()
    
    try:
        asyncio.run(run_batch_demo(count=args.count, headless=args.headless))
    except KeyboardInterrupt:
        print("\n\n[CANCELLED] Demo cancelled by user.")
    except Exception as e:
        print(f"\n\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
    
    print("\nBatch demo complete!")
