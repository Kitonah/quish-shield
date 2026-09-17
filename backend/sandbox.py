from __future__ import annotations

import asyncio
import os
import uuid
from typing import Any, Dict, Optional

from playwright.async_api import async_playwright

SNAPSHOT_DIR = os.path.join(os.path.dirname(__file__), "temp_snapshots")
os.makedirs(SNAPSHOT_DIR, exist_ok=True)

# Common platform warning signatures
INTERSTITIAL_SIGNATURES = [
    "suspected phishing",
    "deceptive site ahead",
    "reported for potential phishing",
    "phishing attack ahead",
    "this website has been reported",
    "account suspended",
    "dangerous site",
]


async def capture_snapshot(url: str) -> Dict[str, Any]:
    """
    Launches headless Playwright Chromium to trace redirects, 
    inspect DOM input elements, and capture a 1280x720 PNG snapshot.
    """
    target_url = url if "://" in url else f"https://{url}"
    screenshot_id = f"{uuid.uuid4().hex}.png"
    screenshot_path = os.path.join(SNAPSHOT_DIR, screenshot_id)

    result = {
        "success": False,
        "resolved_url": target_url,
        "screenshot_path": None,
        "has_credential_inputs": False,
        "is_security_interstitial": False,
        "page_title": None,
        "error": None,
    }

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
            )
            context = await browser.new_context(
                viewport={"width": 1280, "height": 720},
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                ignore_https_errors=True
            )
            page = await context.new_page()

            # Navigate with 8-second ceiling
            response = await page.goto(target_url, wait_until="load", timeout=8000)
            await asyncio.sleep(1.0)  # Allow dynamic scripts to settle

            result["resolved_url"] = page.url
            result["page_title"] = await page.title()

            # 1. Inspect DOM text for platform anti-phishing warnings
            page_text = (await page.content()).lower()
            if any(sig in page_text for sig in INTERSTITIAL_SIGNATURES):
                result["is_security_interstitial"] = True

            # 2. Check DOM for password / credential input fields
            password_inputs = await page.query_selector_all('input[type="password"]')
            otp_inputs = await page.query_selector_all('input[name*="otp"], input[id*="otp"]')
            if len(password_inputs) > 0 or len(otp_inputs) > 0:
                result["has_credential_inputs"] = True

            # 3. Capture Snapshot
            await page.screenshot(path=screenshot_path, full_page=False)
            result["screenshot_path"] = screenshot_path
            result["success"] = True

            await context.close()
            await browser.close()

    except Exception as e:
        result["error"] = str(e)

    return result