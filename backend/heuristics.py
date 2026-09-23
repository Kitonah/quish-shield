from __future__ import annotations

import math
import re
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import httpx
import tldextract

# High-risk TLDs heavily abused in automated phishing kits
SUSPICIOUS_TLDS = {
    "top", "xyz", "club", "buzz", "click", "cam", "fit",
    "work", "gq", "cf", "ml", "ga", "tk", "rest", "surf",
    "beauty", "quest", "cyou", "icu", "skin", "live"
}

# Protected targets for brand abuse / typosquatting
TARGET_BRANDS = [
    "google", "amazon", "apple", "microsoft", "netflix",
    "sbi", "onlinesbi", "hdfc", "icici", "paytm", "phonepe",
    "paypal", "chase", "wellsfargo", "facebook", "instagram"
]

SUSPICIOUS_KEYWORDS = [
    "login", "signin", "verify", "verification", "secure",
    "update", "banking", "account", "recover", "wallet",
    "security", "support", "service", "confirm"
]


def calculate_entropy(text: str) -> float:
    """Calculates Shannon entropy to detect algorithmically generated domains (DGA)."""
    if not text:
        return 0.0
    freq: Dict[str, int] = {}
    for char in text:
        freq[char] = freq.get(char, 0) + 1
    entropy = 0.0
    for count in freq.values():
        p = count / len(text)
        entropy -= p * math.log2(p)
    return round(entropy, 2)


def levenshtein_distance(s1: str, s2: str) -> int:
    """Standard dynamic programming implementation of Levenshtein distance."""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    return previous_row[-1]


async def fetch_rdap_registration_days(registered_domain: str) -> Optional[int]:
    """Queries RDAP to compute age in days."""
    if not registered_domain:
        return None
    url = f"https://rdap.org/domain/{registered_domain}"
    try:
        async with httpx.AsyncClient(timeout=4.0, follow_redirects=True) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                for event in data.get("events", []):
                    if event.get("eventAction") in ("registration", "created"):
                        reg_date = event.get("eventDate")
                        if reg_date:
                            dt = datetime.fromisoformat(reg_date.replace("Z", "+00:00"))
                            now = datetime.now(dt.tzinfo)
                            return max(0, (now - dt).days)
    except Exception:
        pass
    return None


async def inspect_heuristics(target_url: str) -> Dict[str, Any]:
    flags: List[str] = []
    score = 0.0

    parsed = urlparse(target_url if "://" in target_url else f"https://{target_url}")
    hostname = (parsed.hostname or "").lower()
    path_and_query = f"{parsed.path} {parsed.query}".lower()

    ext = tldextract.extract(hostname)
    domain_name = ext.domain.lower()
    subdomain = ext.subdomain.lower()
    suffix = ext.suffix.lower()
    full_fqdn = f"{subdomain}.{domain_name}.{suffix}" if subdomain else f"{domain_name}.{suffix}"

    # 1. IP Host Address
    if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", hostname):
        score += 35.0
        flags.append("Host is a direct raw IP address")

    # 2. Suspicious TLD
    if suffix in SUSPICIOUS_TLDS:
        score += 25.0
        flags.append(f"High-risk top-level domain (.{suffix})")

    # 3. Subdomain Brand Spoofing (e.g. accounts.google.com.something.top)
    is_typosquat = False
    detected_target: Optional[str] = None

    for brand in TARGET_BRANDS:
        # Check if the brand name is prepended in the subdomain to fool users
        if brand in subdomain.split("."):
            score += 45.0
            is_typosquat = True
            detected_target = brand.upper()
            flags.append(f"Subdomain brand impersonation detected: pretending to be {brand.upper()}")
            break
        
        # Typosquatting distance check on the registered root domain
        dist = levenshtein_distance(domain_name, brand)
        if 0 < dist <= 2 and abs(len(domain_name) - len(brand)) <= 2:
            score += 40.0
            is_typosquat = True
            detected_target = brand.upper()
            flags.append(f"Typosquatting detected: resembles {brand.upper()} (edit distance {dist})")
            break

    # 4. Keyword Collision
    matched_keywords = [kw for kw in SUSPICIOUS_KEYWORDS if kw in path_and_query or kw in hostname]
    if len(matched_keywords) >= 2:
        score += 20.0
        flags.append(f"Multiple security/auth keywords: {', '.join(matched_keywords[:4])}")
    elif len(matched_keywords) == 1:
        score += 10.0
        flags.append(f"Suspicious auth keyword: {matched_keywords[0]}")

    # 5. Shannon Entropy
    domain_entropy = calculate_entropy(domain_name)
    if domain_entropy > 3.8:
        score += 20.0
        flags.append(f"High character entropy ({domain_entropy}) - possible DGA domain")

    # 6. RDAP Domain Age Check
    registered_domain = f"{ext.domain}.{ext.suffix}" if ext.domain and ext.suffix else hostname
    age_days = await fetch_rdap_registration_days(registered_domain)
    if age_days is not None:
        if age_days < 14:
            score += 35.0
            flags.append(f"Extremely newly registered domain ({age_days} days old)")
        elif age_days < 90:
            score += 20.0
            flags.append(f"Young domain ({age_days} days old)")

    return {
        "heuristic_score": min(round(score, 1), 100.0),
        "domain_age_days": age_days,
        "is_typosquat": is_typosquat,
        "target_candidate": detected_target,
        "entropy": domain_entropy,
        "flags": flags,
    }