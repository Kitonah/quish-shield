"""
╔══════════════════════════════════════════════════════════════╗
║  QuiShield — Member 3: Headless Sandbox (sandbox.py)         ║
║                                                              ║
║  WHAT THIS FILE DOES (in plain English):                     ║
║  1. Opens an invisible web browser (you won't see a window). ║
║  2. Goes to the URL you give it.                             ║
║  3. Takes a picture (screenshot) of whatever website it      ║
║     lands on — even if the URL bounced through redirects.    ║
║  4. Reads the page's code to see if it has suspicious        ║
║     things like password boxes or OTP fields.                ║
║  5. Returns all of this info as a neat dictionary so other   ║
║     parts of QuiShield can use it.                           ║
╚══════════════════════════════════════════════════════════════╝
"""

import os
import time
import uuid
import asyncio
from urllib.parse import urlparse

from playwright.async_api import async_playwright


# ─── Configuration ────────────────────────────────────────────
SCREENSHOT_DIR = os.path.join(os.path.dirname(__file__), "screenshots")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

# The size of the "virtual screen" the invisible browser uses.
VIEWPORT_WIDTH = 1280
VIEWPORT_HEIGHT = 720

# Maximum seconds to wait for a page to load before giving up.
PAGE_TIMEOUT_MS = 12_000  # 12 seconds


# ─── Helper: detect suspicious form fields ────────────────────
async def _detect_credential_fields(page) -> dict:
    """
    Looks at the page's HTML for form inputs that ask for
    sensitive information (passwords, OTPs, card numbers, etc.).

    Returns a dictionary like:
      {
        "has_password_field": True,
        "has_otp_field": False,
        "has_card_field": False,
        "suspicious_inputs": ["password", "otp", ...]
      }
    """
    # We run JavaScript *inside* the hidden browser page to
    # inspect the form fields. This is safe — it runs in an
    # isolated sandbox, not on your real machine.
    result = await page.evaluate("""
        () => {
            const inputs = Array.from(document.querySelectorAll(
                'input, textarea, select'
            ));

            const dominated = [];

            inputs.forEach(el => {
                const type  = (el.getAttribute('type')        || '').toLowerCase();
                const name  = (el.getAttribute('name')        || '').toLowerCase();
                const id    = (el.getAttribute('id')          || '').toLowerCase();
                const ph    = (el.getAttribute('placeholder') || '').toLowerCase();
                const ac    = (el.getAttribute('autocomplete')|| '').toLowerCase();
                const blob  = `${type} ${name} ${id} ${ph} ${ac}`;
                dominated.push(blob);
            });

            return dominated;
        }
    """)

    # Now we check those collected strings for suspicious keywords.
    password_keywords = ["password", "passwd", "pass", "pwd", "pin"]
    otp_keywords      = ["otp", "one-time", "verification", "verify", "code", "2fa", "mfa"]
    card_keywords     = ["card", "cvv", "cvc", "expiry", "credit", "debit"]
    login_keywords    = ["login", "signin", "sign-in", "log-in", "username", "email",
                         "user", "userid", "account"]

    found = []
    flags = {
        "has_password_field": False,
        "has_otp_field":      False,
        "has_card_field":     False,
        "has_login_field":    False,
    }

    for blob in result:
        for kw in password_keywords:
            if kw in blob:
                flags["has_password_field"] = True
                if "password" not in found:
                    found.append("password")
        for kw in otp_keywords:
            if kw in blob:
                flags["has_otp_field"] = True
                if "otp" not in found:
                    found.append("otp")
        for kw in card_keywords:
            if kw in blob:
                flags["has_card_field"] = True
                if "card" not in found:
                    found.append("card")
        for kw in login_keywords:
            if kw in blob:
                flags["has_login_field"] = True
                if "login" not in found:
                    found.append("login")

    flags["suspicious_inputs"] = found
    return flags


# ─── Helper: extract page metadata ───────────────────────────
async def _extract_page_meta(page) -> dict:
    """
    Grabs the page title and any meta-description tag.
    """
    title = await page.title()
    description = await page.evaluate("""
        () => {
            const meta = document.querySelector('meta[name="description"]');
            return meta ? meta.getAttribute('content') : '';
        }
    """)
    return {"title": title, "description": description}


# ─── Main function: capture_snapshot ──────────────────────────
async def capture_snapshot(url: str) -> dict:
    """
    THE MAIN FUNCTION.

    Give it a URL → it returns a dictionary with:
      - screenshot_path : where the image was saved
      - final_url       : the URL after all redirects
      - redirected      : True/False — did the URL bounce?
      - page_title      : title of the page
      - page_description: meta description
      - credential_fields: info about suspicious form fields
      - load_time_ms    : how long the page took to load
      - error           : any error message (None if all good)

    HOW TO USE:
        import asyncio
        from sandbox import capture_snapshot

        result = asyncio.run(capture_snapshot("https://example.com"))
        print(result)
    """

    # Generate a unique filename for the screenshot so we never
    # overwrite a previous one.
    snap_id = uuid.uuid4().hex[:10]
    screenshot_path = os.path.join(SCREENSHOT_DIR, f"snap_{snap_id}.png")

    # Build the result dictionary with safe defaults.
    result = {
        "snapshot_id":        snap_id,
        "original_url":       url,
        "final_url":          url,
        "redirected":         False,
        "redirect_chain":     [],
        "screenshot_path":    screenshot_path,
        "page_title":         "",
        "page_description":   "",
        "credential_fields":  {},
        "load_time_ms":       0,
        "error":              None,
    }

    # ── Launch the invisible browser ──────────────────────────
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,           # No visible window
            args=[
                "--no-sandbox",
                "--disable-gpu",
                "--disable-dev-shm-usage",
                "--disable-extensions",
            ],
        )

        # Create a fresh, isolated "browser tab" (context).
        context = await browser.new_context(
            viewport={"width": VIEWPORT_WIDTH, "height": VIEWPORT_HEIGHT},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            ignore_https_errors=True,   # Don't crash on bad SSL
        )

        page = await context.new_page()

        # Track redirects: every time the browser bounces to a
        # new URL, we record it.
        redirect_chain = []

        def _on_response(response):
            status = response.status
            if 300 <= status < 400:
                redirect_chain.append({
                    "url":    response.url,
                    "status": status,
                })

        page.on("response", _on_response)

        try:
            start = time.time()

            # Actually navigate to the URL.
            await page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=PAGE_TIMEOUT_MS,
            )

            # Wait a tiny bit for JS-heavy pages to finish rendering.
            await page.wait_for_timeout(1500)

            elapsed_ms = int((time.time() - start) * 1000)
            result["load_time_ms"] = elapsed_ms

            # Where did we actually end up?
            final_url = page.url
            result["final_url"]       = final_url
            result["redirected"]      = (final_url != url)
            result["redirect_chain"]  = redirect_chain

            # Take the screenshot.
            await page.screenshot(path=screenshot_path, full_page=False)

            # Detect credential-harvesting fields.
            creds = await _detect_credential_fields(page)
            result["credential_fields"] = creds

            # Grab page metadata.
            meta = await _extract_page_meta(page)
            result["page_title"]       = meta["title"]
            result["page_description"] = meta["description"]

        except Exception as exc:
            # If anything went wrong (timeout, DNS failure, etc.)
            # we still return a result — just with the error noted.
            result["error"] = str(exc)

            # Try to grab a screenshot even on error (might show
            # the browser's error page, which is still useful).
            try:
                await page.screenshot(path=screenshot_path, full_page=False)
            except Exception:
                result["screenshot_path"] = None

        finally:
            await context.close()
            await browser.close()

    return result


# ─── Quick self-test ──────────────────────────────────────────
if __name__ == "__main__":
    import json

    test_url = "https://example.com"
    print(f"\n🔍 Testing sandbox with: {test_url}\n")
    output = asyncio.run(capture_snapshot(test_url))
    print(json.dumps(output, indent=2))
