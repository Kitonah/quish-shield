from __future__ import annotations

import asyncio
import os
import time
import uuid
from typing import Any, Dict

from playwright.async_api import async_playwright

SNAPSHOT_DIR = os.path.join(os.path.dirname(__file__), "temp_snapshots")
os.makedirs(SNAPSHOT_DIR, exist_ok=True)

INTERSTITIAL_SIGNATURES = [
    "suspected phishing",
    "deceptive site ahead",
    "reported for potential phishing",
    "phishing attack ahead",
    "this website has been reported",
    "account suspended",
    "dangerous site",
    "cloudflare-interstitial",
    "the site ahead contains malware",
    "potential phishing",
    "phishing is when a site attempts to steal",
    "warning: suspected phishing",
    "threat detected",
]

TAKEDOWN_NETWORK_ERRORS = [
    "err_connection_reset",
    "err_connection_refused",
    "err_name_not_resolved",
    "err_ssl_protocol_error",
    "err_tunnel_connection_failed",
]

CREDENTIAL_SELECTORS = [
    'input[type="password"]',
    'input[name*="pass" i]',
    'input[id*="pass" i]',
    'input[name*="otp" i]',
    'input[id*="otp" i]',
    'input[name*="pin" i]',
    'input[id*="pin" i]',
    'input[name*="cvv" i]',
    'input[id*="cvv" i]',
    'input[name*="card" i]',
    'input[id*="card" i]',
]


async def capture_snapshot(url: str) -> Dict[str, Any]:
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
        "load_time_ms": 0.0,
        "error": None,
    }

    start_time = time.perf_counter()
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled",
                ],
            )
            context = await browser.new_context(
                viewport={"width": 1280, "height": 720},
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                ignore_https_errors=True,
            )
            page = await context.new_page()

            await page.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )

            # Navigate using commit first so HTTP responses are not lost
            response = await page.goto(target_url, wait_until="commit", timeout=9000)
            await page.wait_for_load_state("domcontentloaded", timeout=3000)
            await asyncio.sleep(1.0)

            result["resolved_url"] = page.url
            result["page_title"] = await page.title()
            result["load_time_ms"] = round((time.perf_counter() - start_time) * 1000, 2)

            # Check for legal/takedown HTTP responses
            if response and response.status in (403, 451):
                result["is_security_interstitial"] = True

            # Inspect rendered content and visible body text
            raw_html = (await page.content()).lower()
            try:
                body_text = (await page.inner_text("body", timeout=1500)).lower()
            except Exception:
                body_text = ""

            combined_text = f"{raw_html} {body_text}"
            if any(sig in combined_text for sig in INTERSTITIAL_SIGNATURES):
                result["is_security_interstitial"] = True

            # Credential harvester checks
            combined_selector = ", ".join(CREDENTIAL_SELECTORS)
            cred_elements = await page.query_selector_all(combined_selector)
            if len(cred_elements) > 0:
                result["has_credential_inputs"] = True

            await page.screenshot(path=screenshot_path, full_page=False)
            result["screenshot_path"] = screenshot_path
            result["success"] = True

            await context.close()
            await browser.close()

    except Exception as e:
        err_msg = str(e)
        result["error"] = err_msg
        result["load_time_ms"] = round((time.perf_counter() - start_time) * 1000, 2)

        # Catch active network-level resets and registrar takedowns
        err_lower = err_msg.lower()
        if any(token in err_lower for token in TAKEDOWN_NETWORK_ERRORS):
            result["is_security_interstitial"] = True

    return result