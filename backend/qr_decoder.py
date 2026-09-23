from __future__ import annotations

import io
import re
from typing import Any, Dict, List
from urllib.parse import unquote

import cv2
import httpx
import numpy as np
from PIL import Image

TRACKING_GATEWAYS = (
    "me-qr.com",
    "qr1.me-qr.com",
    "q.me-qr.com",
    "qr-code-generator.com",
    "qrco.de",
    "tinyurl.com",
    "bit.ly",
)


class QRDecoder:
    @classmethod
    def resolve_url(cls, url: str, timeout: float = 6.0) -> str:
        """
        Unrolls redirects, shorteners, and intermediate tracking redirect gateways.
        Extracts hidden destination targets from dynamic ad-wall landing pages.
        """
        if not url.startswith(("http://", "https://")):
            return url

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

        try:
            with httpx.Client(follow_redirects=True, timeout=timeout, headers=headers) as client:
                resp = client.get(url)
                final_url = str(resp.url)

                # Check if landed on a known tracking intermediary
                if any(gw in final_url.lower() for gw in TRACKING_GATEWAYS):
                    body = resp.text

                    # 1. Look for unquoted URL parameters in links or script tags (e.g. ?url=... or &dest=...)
                    param_match = re.search(r'(?:url|redirect|target|link|dest)=([a-zA-Z0-9%\-\._~:/?#\[\]@!$&\'()*+,;=]+)', body, re.IGNORECASE)
                    if param_match:
                        raw_target = unquote(param_match.group(1))
                        if raw_target.startswith(("http://", "https://")) and not any(gw in raw_target.lower() for gw in TRACKING_GATEWAYS):
                            return raw_target

                    # 2. Look for JavaScript object literals like { destination: "...", redirect_url: "..." }
                    json_match = re.search(r'["\'](?:destination_url|redirect_url|original_url|target_url)["\']\s*:\s*["\'](https?://[^"\']+)["\']', body, re.IGNORECASE)
                    if json_match:
                        return json_match.group(1)

                    # 3. Look for explicit meta refresh tags
                    meta_match = re.search(r'content=["\']\d+;\s*url=([^"\']+)["\']', body, re.IGNORECASE)
                    if meta_match:
                        target = meta_match.group(1).strip()
                        if target.startswith("http") and not any(gw in target.lower() for gw in TRACKING_GATEWAYS):
                            return target

                    # 4. Fallback: Parse DOM using Playwright to extract final button navigation
                    try:
                        return cls._extract_with_browser(final_url)
                    except Exception:
                        pass

                return final_url
        except Exception:
            return url

    @staticmethod
    def _extract_with_browser(url: str) -> str:
        """Runs a brief Playwright browser session to extract destination links from ad walls."""
        from playwright.sync_api import sync_playwright

        resolved_url = url
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-blink-features=AutomationControlled"],
            )
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                )
            )
            page = context.new_page()
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=7000)
                page.wait_for_timeout(1500)

                # Find any anchor tag pointing off the tracker domain
                links = page.query_selector_all("a[href^='http']")
                for link in links:
                    href = link.get_attribute("href")
                    if href and not any(gw in href.lower() for gw in TRACKING_GATEWAYS):
                        resolved_url = href
                        break
            except Exception:
                resolved_url = url
            finally:
                context.close()
                browser.close()
        return resolved_url

    @classmethod
    def _preprocess_image(cls, image_bytes: bytes) -> np.ndarray:
        """Flattens transparency onto a solid white background and converts to BGR."""
        pil_img = Image.open(io.BytesIO(image_bytes))

        if pil_img.mode in ("RGBA", "LA") or (pil_img.mode == "P" and "transparency" in pil_img.info):
            canvas = Image.new("RGBA", pil_img.size, (255, 255, 255, 255))
            canvas.paste(pil_img, mask=pil_img.split()[-1])
            pil_img = canvas.convert("RGB")
        else:
            pil_img = pil_img.convert("RGB")

        return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

    @classmethod
    def _multi_pass_decode(cls, img: np.ndarray) -> str:
        detector = cv2.QRCodeDetector()

        h, w = img.shape[:2]
        pad = max(60, int(min(h, w) * 0.15))

        padded = cv2.copyMakeBorder(
            img, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=[255, 255, 255]
        )

        gray = cv2.cvtColor(padded, cv2.COLOR_BGR2GRAY)
        _, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
        scaled = cv2.resize(padded, (w * 2, h * 2), interpolation=cv2.INTER_CUBIC)

        candidates = [padded, gray, otsu, scaled, img]

        for cand in candidates:
            try:
                data, _, _ = detector.detectAndDecode(cand)
                if data and data.strip():
                    return data.strip()
            except Exception:
                continue

        try:
            from pyzbar.pyzbar import decode as zbar_decode
            zbar_results = zbar_decode(padded)
            for item in zbar_results:
                if item.data:
                    return item.data.decode("utf-8").strip()
        except Exception:
            pass

        return ""

    @classmethod
    def decode_image(cls, image_bytes: bytes) -> Dict[str, Any]:
        if not image_bytes:
            return {
                "found": False,
                "raw_data": None,
                "resolved_url": None,
                "is_upi": False,
            }

        try:
            img = cls._preprocess_image(image_bytes)
        except Exception:
            return {
                "found": False,
                "raw_data": None,
                "resolved_url": None,
                "is_upi": False,
            }

        clean_data = cls._multi_pass_decode(img)

        if not clean_data:
            return {
                "found": False,
                "raw_data": None,
                "resolved_url": None,
                "is_upi": False,
            }

        is_upi = clean_data.startswith("upi://")
        is_web = clean_data.startswith(("http://", "https://"))

        resolved = cls.resolve_url(clean_data) if is_web else None

        return {
            "found": True,
            "raw_data": clean_data,
            "resolved_url": resolved,
            "is_upi": is_upi,
        }

    @classmethod
    def parse_sms(cls, text: str) -> List[Dict[str, str]]:
        if not text:
            return []

        url_pattern = r"(https?://[^\s]+)"
        found = re.findall(url_pattern, text)

        results = []
        for raw in set(found):
            cleaned_raw = raw.rstrip(".,!?;:)\"'>]")
            resolved = cls.resolve_url(cleaned_raw)
            results.append({"original": cleaned_raw, "resolved": resolved})

        return results