from __future__ import annotations

import math
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import httpx
import Levenshtein
import tldextract
import whois

# High-profile brand targets for typosquat detection
TARGET_BRANDS = {
    "sbi": ["onlinesbi.sbi", "sbi.co.in"],
    "hdfc": ["hdfcbank.com"],
    "icici": ["icicibank.com"],
    "amazon": ["amazon.in", "amazon.com"],
    "google": ["google.com", "google.co.in", "youtube.com"],
    "paytm": ["paytm.com"],
    "phonepe": ["phonepe.com"],
    "incometax": ["incometax.gov.in"],
}

# Free ephemeral / cloud hosting providers often abused for phishing
FREE_HOSTING_PROVIDERS = {
    "pages.dev", "workers.dev", "web.app", "firebaseapp.com",
    "netlify.app", "vercel.app", "glitch.me", "ngrok-free.app", "github.io"
}

SUSPICIOUS_TLDS = {".xyz", ".top", ".club", ".work", ".click", ".buzz", ".live", ".icu", ".cam"}
SUSPICIOUS_KEYWORDS = ["secure", "login", "verify", "update", "banking", "account", "kyc", "otp", "signin"]


def calculate_entropy(text: str) -> float:
    """Compute Shannon Entropy of a string."""
    if not text:
        return 0.0
    freq = {c: text.count(c) / len(text) for c in set(text)}
    return -sum(p * math.log2(p) for p in freq.values())


async def get_domain_age_days(domain: str) -> Optional[int]:
    """Resolve domain age using ICANN RDAP with WHOIS fallback."""
    if not domain:
        return None

    # Primary: ICANN RDAP REST over HTTPS
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"https://rdap.org/domain/{domain}")
            if resp.status_code == 200:
                data = resp.json()
                for event in data.get("events", []):
                    if event.get("eventAction") == "registration":
                        reg_date = datetime.fromisoformat(event["eventDate"].replace("Z", "+00:00"))
                        return (datetime.now(timezone.utc) - reg_date).days
    except Exception:
        pass

    # Fallback: WHOIS socket query
    try:
        w = whois.whois(domain)
        creation_date = w.creation_date
        if isinstance(creation_date, list):
            creation_date = creation_date[0]
        if creation_date:
            if creation_date.tzinfo is None:
                creation_date = creation_date.replace(tzinfo=timezone.utc)
            return (datetime.now(timezone.utc) - creation_date).days
    except Exception:
        pass

    return None


async def inspect_heuristics(url: str) -> Dict[str, Any]:
    """Execute complete lexical domain heuristics and RDAP check."""
    flags: List[str] = []
    score = 0.0

    parsed = urlparse(url if "://" in url else f"http://{url}")
    host = parsed.netloc.lower()

    ext = tldextract.extract(url)
    domain_name = ext.domain.lower()
    suffix = ext.suffix.lower()
    subdomain = ext.subdomain.lower()
    registered_domain = f"{domain_name}.{suffix}" if ext.domain and ext.suffix else host

    # 1. IP Host Check
    if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", host.split(":")[0]):
        flags.append("Host is a direct raw IP address")
        score += 35.0

    # 2. Suspicious TLD
    for tld in SUSPICIOUS_TLDS:
        if registered_domain.endswith(tld):
            flags.append(f"Suspicious high-risk TLD: {tld}")
            score += 20.0
            break

    # 3. Free Cloud Hosting Abused as Phishing Subdomain
    if any(registered_domain.endswith(provider) for provider in FREE_HOSTING_PROVIDERS):
        flags.append(f"Hosted on free cloud platform ({registered_domain})")
        score += 25.0

    # 4. Deceptive Subdomains & Keywords
    found_keywords = [kw for kw in SUSPICIOUS_KEYWORDS if kw in parsed.path.lower() or kw in subdomain]
    if found_keywords:
        flags.append(f"Suspicious security keywords found: {', '.join(found_keywords)}")
        score += 15.0

    # 5. Shannon Entropy (Random algorithmic domains)
    entropy = calculate_entropy(domain_name)
    if entropy > 3.8 and len(domain_name) > 10:
        flags.append(f"High domain randomness (Entropy: {entropy:.2f})")
        score += 15.0

    # 6. Typosquatting Match via Levenshtein Distance
    is_typosquat = False
    target_candidate = None

    for brand, canonical_domains in TARGET_BRANDS.items():
        canonical_roots = [tldextract.extract(d).domain.lower() for d in canonical_domains]
        if domain_name in canonical_roots:
            continue  # Exact match to legitimate domain

        # Check distance
        for c_root in canonical_roots:
            dist = Levenshtein.distance(domain_name, c_root)
            if 0 < dist <= 2 and len(domain_name) >= 4:
                is_typosquat = True
                target_candidate = brand.upper()
                flags.append(f"Typosquatting detected: resembles {brand.upper()} (Edit Distance: {dist})")
                score += 45.0
                break
        if is_typosquat:
            break

    # 7. Domain Age Check
    domain_age = await get_domain_age_days(registered_domain)
    if domain_age is not None:
        if domain_age < 30:
            flags.append(f"Newly registered domain ({domain_age} days old)")
            score += 30.0

    return {
        "heuristic_score": min(round(score, 1), 100.0),
        "domain_age_days": domain_age,
        "is_typosquat": is_typosquat,
        "target_candidate": target_candidate,
        "flags": flags,
    }