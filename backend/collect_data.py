"""
+======================================================================+
|  QuiShield -- collect_data.py                                         |
|                                                                       |
|  WHAT THIS FILE DOES (in plain English):                              |
|  Uses YOUR sandbox (sandbox.py) to automatically visit real brand     |
|  websites and take screenshots. It saves them in organized folders    |
|  so the training script can learn from them later.                    |
|                                                                       |
|  HOW TO RUN:                                                          |
|    python collect_data.py                                             |
|                                                                       |
|  This will create a training_data/ folder with subfolders for each   |
|  brand, each containing 20-40 screenshots.                           |
+======================================================================+
"""

import os
import sys
import asyncio
import random
import time
from pathlib import Path

# We reuse your existing sandbox to capture screenshots.
from sandbox import SCREENSHOT_DIR

# We import playwright directly here because we need more control
# over viewport sizes and scroll positions than capture_snapshot gives.
from playwright.async_api import async_playwright


# ---- Configuration -----------------------------------------------------------

# Where to store the training data
DATA_DIR = os.path.join(os.path.dirname(__file__), "training_data")

# The brands we want to teach the model to recognize.
# Each entry has:
#   - "label": The folder name / class name
#   - "urls": A list of real pages to screenshot
BRAND_CONFIGS = [
    {
        "label": "sbi",
        "urls": [
            "https://www.onlinesbi.sbi/",
            "https://retail.onlinesbi.sbi/retail/login.htm",
            "https://www.sbi.co.in/",
            "https://www.sbi.co.in/web/personal-banking",
            "https://www.sbi.co.in/web/personal-banking/accounts",
            "https://www.sbicardlogin.com/",
            "https://www.sbi.co.in/web/interest-rates/deposit-rates",
        ],
    },
    {
        "label": "hdfc",
        "urls": [
            "https://www.hdfcbank.com/",
            "https://www.hdfcbank.com/personal",
            "https://www.hdfcbank.com/personal/save",
            "https://www.hdfcbank.com/personal/borrow",
            "https://www.hdfcbank.com/personal/invest",
            "https://netbanking.hdfcbank.com/netbanking/",
            "https://www.hdfcbank.com/personal/resources/rates",
        ],
    },
    {
        "label": "icici",
        "urls": [
            "https://www.icicibank.com/",
            "https://www.icicibank.com/personal-banking",
            "https://www.icicibank.com/personal-banking/accounts",
            "https://infinity.icicibank.com/corp/AuthenticationController",
            "https://www.icicibank.com/personal-banking/loans",
            "https://www.icicibank.com/personal-banking/cards",
        ],
    },
    {
        "label": "paytm",
        "urls": [
            "https://paytm.com/",
            "https://paytm.com/recharge",
            "https://paytm.com/electricity-bill-payment",
            "https://paytm.com/gas-bill-payment",
            "https://paytm.com/water-bill-payment",
            "https://paytm.com/insurance",
        ],
    },
    {
        "label": "google",
        "urls": [
            "https://accounts.google.com/",
            "https://accounts.google.com/signin",
            "https://www.google.com/",
            "https://myaccount.google.com/",
            "https://mail.google.com/",
            "https://drive.google.com/",
        ],
    },
    {
        "label": "incometax",
        "urls": [
            "https://www.incometax.gov.in/iec/foportal/",
            "https://eportal.incometax.gov.in/iec/foservices/#/login",
            "https://www.incometax.gov.in/iec/foportal/help/all-topics",
            "https://eportal.incometax.gov.in/iec/foservices/#/pre-login/register",
            "https://www.incometax.gov.in/iec/foportal/help/how-to-file-itr",
        ],
    },
    {
        "label": "amazon",
        "urls": [
            "https://www.amazon.in/",
            "https://www.amazon.in/ap/signin",
            "https://www.amazon.in/gp/goldbox",
            "https://www.amazon.in/gp/bestsellers",
            "https://www.amazon.in/gp/help/customer/display.html",
        ],
    },
    {
        "label": "phonepe",
        "urls": [
            "https://www.phonepe.com/",
            "https://www.phonepe.com/business/",
            "https://www.phonepe.com/about-us/",
            "https://www.phonepe.com/careers/",
            "https://www.phonepe.com/blog/",
        ],
    },
    {
        "label": "unknown",
        "urls": [
            "https://www.wikipedia.org/",
            "https://en.wikipedia.org/wiki/Phishing",
            "https://stackoverflow.com/",
            "https://www.reddit.com/",
            "https://news.ycombinator.com/",
            "https://www.bbc.com/",
            "https://www.github.com/",
            "https://www.python.org/",
            "https://www.mozilla.org/",
            "https://www.w3schools.com/",
            "https://example.com/",
            "https://httpbin.org/",
            "https://www.rust-lang.org/",
            "https://www.figma.com/",
        ],
    },
]

# Different viewport sizes to add variety to our training data.
# This teaches the model that pages can look different at different
# screen sizes but still belong to the same brand.
VIEWPORTS = [
    {"width": 1280, "height": 720},
    {"width": 1366, "height": 768},
    {"width": 1024, "height": 600},
    {"width": 1440, "height": 900},
]

# Scroll positions (in pixels from top) for variety.
SCROLL_POSITIONS = [0, 300, 600]

# Timeout for each page load (milliseconds)
PAGE_TIMEOUT = 15000


# ---- Core capture function ---------------------------------------------------

async def capture_brand_screenshot(
    page,
    url: str,
    save_path: str,
    scroll_y: int = 0,
) -> bool:
    """
    Navigate to a URL, optionally scroll down, and save a screenshot.
    Returns True on success, False on failure.
    """
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=PAGE_TIMEOUT)
        await page.wait_for_timeout(2000)  # Let JS finish rendering

        if scroll_y > 0:
            await page.evaluate(f"window.scrollTo(0, {scroll_y})")
            await page.wait_for_timeout(500)

        await page.screenshot(path=save_path, full_page=False)
        return True

    except Exception as e:
        print(f"    [SKIP] {url} -- {str(e)[:80]}")
        return False


# ---- Main collection loop ---------------------------------------------------

async def collect_all():
    """
    Goes through every brand config, visits each URL with different
    viewports and scroll positions, and saves screenshots.
    """
    total_captured = 0
    total_failed = 0

    async with async_playwright() as pw:
        for brand_config in BRAND_CONFIGS:
            label = brand_config["label"]
            urls = brand_config["urls"]

            # Create the folder for this brand
            brand_dir = os.path.join(DATA_DIR, label)
            os.makedirs(brand_dir, exist_ok=True)

            print(f"\n{'='*50}")
            print(f"  Collecting: {label.upper()}")
            print(f"  URLs: {len(urls)}  |  Viewports: {len(VIEWPORTS)}  |  Scrolls: {len(SCROLL_POSITIONS)}")
            print(f"{'='*50}")

            img_index = 0

            for url in urls:
                # Pick a random subset of viewports for this URL
                # (we don't need ALL combinations for every URL)
                vp_sample = random.sample(VIEWPORTS, min(2, len(VIEWPORTS)))

                for vp in vp_sample:
                    # Launch a fresh browser context for each viewport
                    browser = await pw.chromium.launch(
                        headless=True,
                        args=["--no-sandbox", "--disable-gpu",
                              "--disable-dev-shm-usage"],
                    )
                    context = await browser.new_context(
                        viewport=vp,
                        user_agent=(
                            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/120.0.0.0 Safari/537.36"
                        ),
                        ignore_https_errors=True,
                    )
                    page = await context.new_page()

                    # Pick 1-2 random scroll positions
                    scroll_sample = random.sample(
                        SCROLL_POSITIONS,
                        min(2, len(SCROLL_POSITIONS)),
                    )

                    for scroll_y in scroll_sample:
                        filename = f"{label}_{img_index:04d}.png"
                        save_path = os.path.join(brand_dir, filename)

                        success = await capture_brand_screenshot(
                            page, url, save_path, scroll_y
                        )

                        if success:
                            total_captured += 1
                            img_index += 1
                            print(f"    [OK] {filename}  ({vp['width']}x{vp['height']}, scroll={scroll_y})")
                        else:
                            total_failed += 1

                    await context.close()
                    await browser.close()

            print(f"  -> {img_index} images saved to training_data/{label}/")

    print(f"\n{'='*50}")
    print(f"  COLLECTION COMPLETE")
    print(f"  Total captured: {total_captured}")
    print(f"  Total failed:   {total_failed}")
    print(f"  Data folder:    {DATA_DIR}")
    print(f"{'='*50}\n")


# ---- Entry point -------------------------------------------------------------

if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("  [QuiShield] Training Data Collector")
    print("  This will visit real websites and take screenshots.")
    print("  Make sure you have internet access.")
    print("=" * 50)

    asyncio.run(collect_all())
