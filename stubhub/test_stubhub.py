"""
Test script for StubHub verifier.
Run with: python navi_bench/stubhub/test_stubhub.py
Or: pytest navi_bench/stubhub/test_stubhub.py -v
"""

import asyncio
import json
import pytest
from playwright.async_api import async_playwright

from navi_bench.base import DatasetItem, instantiate


@pytest.mark.asyncio
async def test_scraper_on_real_page():
    """Test the JavaScript scraper on a real StubHub page."""
    print("=" * 60)
    print("Testing StubHub JavaScript Scraper")
    print("=" * 60)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Test 1: Navigate to StubHub search
        print("\n[Test 1] Loading StubHub search page...")
        await page.goto("https://www.stubhub.com/")
        await page.wait_for_timeout(2000)
        
        # Search for Lakers
        print("[Test 1] Searching for 'Lakers'...")
        search_box = await page.query_selector('input[type="search"]')
        if search_box:
            await search_box.fill("Lakers")
            await search_box.press("Enter")
            await page.wait_for_timeout(3000)
        
        # Load and execute the scraper
        print("[Test 1] Running JavaScript scraper...")
        with open("navi_bench/stubhub/stubhub_info_gathering.js", "r") as f:
            js_script = f.read()
        
        results = await page.evaluate(js_script)
        print(f"[Test 1] Extracted {len(results)} results")
        
        if results:
            print("\n[Test 1] Sample result:")
            print(json.dumps(results[0], indent=2))
        else:
            print("\n[Test 1] [WARN] No results extracted - may need selector updates")
        
        await browser.close()
    
    print("\n" + "=" * 60)
    print("Scraper Test Complete")
    print("=" * 60)


@pytest.mark.asyncio
async def test_verifier_with_dataset():
    """Test the Python verifier with a dataset item."""
    print("\n" + "=" * 60)
    print("Testing StubHub Python Verifier")
    print("=" * 60)
    
    dataset_row = {
        "task_id": "navi_bench/stubhub/lakers_test/0",
        "task_generation_config_json": json.dumps({
            "_target_": "navi_bench.stubhub.stubhub_info_gathering.generate_task_config_deterministic",
            "mode": "any",
            "url": "https://www.stubhub.com",
            "task": "Search for Lakers tickets in Los Angeles for December 20, 2025 under $500",
            "queries": [[{
                "event_names": ["lakers", "los angeles lakers", "la lakers"],
                "dates": ["2025-12-20"],
                "cities": ["los angeles", "inglewood"],
                "max_price": 500.00
            }]],
            "location": "Los Angeles, CA, United States",
            "timezone": "America/Los_Angeles",
        }),
        "env": "real",
        "domain": "stubhub",
        "l1_category": "entertainment",
        "l2_category": "sports",
    }
    
    print("\n[Test] Creating dataset item...")
    dataset_item = DatasetItem.model_validate(dataset_row)
    
    print("[Test] Generating task config...")
    task_config = dataset_item.generate_task_config()
    
    print("[Test] Instantiating evaluator...")
    evaluator = instantiate(task_config.eval_config)
    
    print("\n[Test] Task:", task_config.task)
    print("[Test] Evaluator:", evaluator)
    
    # Test with Playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        print("\n[Test] Navigating to StubHub...")
        await page.goto("https://www.stubhub.com/")
        await page.wait_for_timeout(2000)
        
        # Search for Lakers
        search_box = await page.query_selector('input[type="search"]')
        if search_box:
            await search_box.fill("Lakers December 20")
            await search_box.press("Enter")
            await page.wait_for_timeout(3000)
        
        print("[Test] Updating evaluator with page data...")
        await evaluator.update(page=page)
        
        print("[Test] Computing result...")
        result = await evaluator.compute()
        
        print("\n" + "=" * 60)
        print("VERIFICATION RESULT")
        print("=" * 60)
        print(f"Score: {result.score}")
        print(f"Queries covered: {result.n_covered}/{result.n_queries}")
        print(f"Coverage: {result.score * 100:.1f}%")
        
        if result.score == 1.0:
            print("[PASS] SUCCESS: All queries covered!")
        else:
            print("[WARN] PARTIAL: Some queries not covered")
        
        await browser.close()
    
    print("=" * 60)


async def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("STUBHUB VERIFIER TEST SUITE")
    print("=" * 60)
    
    try:
        # Test 1: Scraper
        await test_scraper_on_real_page()
        
        # Test 2: Verifier
        await test_verifier_with_dataset()
        
        print("\n" + "=" * 60)
        print("ALL TESTS COMPLETE")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
