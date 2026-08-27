import asyncio
import math
import pprint
import re
import warnings
from datetime import datetime
from typing import Optional, Tuple
from urllib.parse import urlparse
import httpx
import tldextract
import whois

warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=UserWarning)

TARGET_WHITELIST = {
    "onlinesbi.sbi": "State Bank of India",
    "onlinesbi.com": "State Bank of India",
    "hdfcbank.com": "HDFC Bank",
    "icicibank.com": "ICICI Bank",
    "axisbank.com": "Axis Bank",
    "kotak.com": "Kotak Mahindra Bank",
    "incometax.gov.in": "Income Tax Department",
    "uidai.gov.in": "UIDAI",
    "digilocker.gov.in": "DigiLocker",
    "amazon.in": "Amazon India",
    "amazon.com": "Amazon",
    "flipkart.com": "Flipkart",
    "paytm.com": "Paytm",
}

SUSPICIOUS_TLDS = {
    "xyz", "top", "live", "click", "work", "loan", "club",
    "gq", "cf", "tk", "ml", "ga", "buzz", "rest", "fit", "surf"
}

SUSPICIOUS_KEYWORDS = [
    "login", "verify", "secure", "banking", "update", "kyc",
    "account", "signin", "support", "service", "pan-update"
]


def calculate_entropy(text: str) -> float:
    if not text:
        return 0.0
    entropy = 0.0
    for x in set(text):
        p_x = float(text.count(x)) / len(text)
        entropy += - p_x * math.log2(p_x)
    return round(entropy, 2)


def check_typosquatting(domain: str) -> Tuple[bool, Optional[str], Optional[str]]:
    import Levenshtein

    clean_domain = domain.lower()
    if clean_domain in TARGET_WHITELIST:
        return False, clean_domain, TARGET_WHITELIST[clean_domain]

    for target, brand in TARGET_WHITELIST.items():
        dist = Levenshtein.distance(clean_domain, target)
        if 0 < dist <= 2 and abs(len(clean_domain) - len(target)) <= 2:
            return True, target, brand

    return False, None, None


async def query_rdap_age_days(domain: str) -> Optional[int]:
    """Official ICANN RDAP REST lookup over HTTPS (bypasses WHOIS port-43 blocking)."""
    try:
        async with httpx.AsyncClient(timeout=3.0, follow_redirects=True) as client:
            resp = await client.get(f"https://rdap.org/domain/{domain}")
            if resp.status_code == 200:
                data = resp.json()
                for event in data.get("events", []):
                    if event.get("eventAction") in ["registration", "created"]:
                        date_str = event.get("eventDate", "").split("T")[0]
                        created_dt = datetime.strptime(date_str, "%Y-%m-%d")
                        return max((datetime.now() - created_dt).days, 0)
    except Exception:
        pass
    return None


def get_whois_age_days_sync(domain: str) -> Optional[int]:
    """Fallback WHOIS socket query."""
    try:
        w = whois.whois(domain)
        creation_date = getattr(w, "creation_date", None)
        if isinstance(creation_date, list):
            creation_date = creation_date[0]
        if isinstance(creation_date, datetime):
            return max((datetime.now() - creation_date).days, 0)
    except Exception:
        pass
    return None


async def get_domain_age_days(domain: str) -> Optional[int]:
    """Tries RDAP first, falls back to WHOIS."""
    age = await query_rdap_age_days(domain)
    if age is not None:
        return age

    try:
        loop = asyncio.get_running_loop()
        return await asyncio.wait_for(
            loop.run_in_executor(None, get_whois_age_days_sync, domain),
            timeout=2.5
        )
    except Exception:
        return None


async def inspect_heuristics(url: str) -> dict:
    flags = []
    score = 0.0

    formatted_url = url.strip()
    if not formatted_url.startswith(("http://", "https://")):
        formatted_url = f"http://{formatted_url}"

    try:
        parsed_url = urlparse(formatted_url)
        extracted = tldextract.extract(formatted_url)
    except Exception as e:
        return {
            "heuristic_score": 100.0,
            "domain_age_days": None,
            "is_typosquat": False,
            "target_candidate": None,
            "flags": [f"Malformed URL: {str(e)}"]
        }

    domain_name = extracted.domain.lower()
    tld = extracted.suffix.lower()
    subdomain = extracted.subdomain.lower()
    path = parsed_url.path.lower()
    netloc = parsed_url.netloc.lower()

    registered_domain = f"{domain_name}.{tld}" if domain_name and tld else ""

    if not registered_domain and not re.match(r"^\d{1,3}(\.\d{1,3}){3}", netloc):
        return {
            "heuristic_score": 80.0,
            "domain_age_days": None,
            "is_typosquat": False,
            "target_candidate": None,
            "flags": ["Invalid or Unresolvable Domain Structure"]
        }

    # 1. IP Address Check
    if re.match(r"^\d{1,3}(\.\d{1,3}){3}", netloc):
        flags.append("Host is a direct raw IP address")
        score += 35.0

    # 2. Suspicious TLD
    if tld in SUSPICIOUS_TLDS:
        flags.append(f"High-risk TLD (.{tld})")
        score += 20.0

    # 3. Shannon Entropy
    domain_entropy = calculate_entropy(domain_name)
    if domain_entropy > 3.8 and len(domain_name) > 10:
        flags.append(f"High domain entropy ({domain_entropy})")
        score += 15.0

    if len(subdomain.split(".")) >= 3:
        flags.append("Excessive subdomain depth")
        score += 15.0

    # 4. Deceptive Subdomains
    target_candidate = None
    for brand_key, brand_name in TARGET_WHITELIST.items():
        brand_core = brand_key.split(".")[0]
        if brand_core in subdomain and brand_core not in domain_name:
            flags.append(f"Deceptive subdomain impersonating {brand_name}")
            target_candidate = brand_name
            score += 40.0
            break

    # 5. Security Keyword Stuffing
    matched_keywords = [kw for kw in SUSPICIOUS_KEYWORDS if kw in path or kw in subdomain]
    if matched_keywords:
        flags.append(f"Suspicious security keywords detected: {', '.join(matched_keywords)}")
        score += min(len(matched_keywords) * 10.0, 25.0)

    # 6. Typosquatting
    is_typosquat, squat_target, squat_brand = check_typosquatting(registered_domain)
    if is_typosquat:
        flags.append(f"Typosquatting detected: mimics {squat_target} ({squat_brand})")
        target_candidate = squat_brand
        score += 45.0

    # 7. Domain Age Resolution
    domain_age_days = None
    if registered_domain:
        domain_age_days = await get_domain_age_days(registered_domain)
        if domain_age_days is None:
            flags.append("WHOIS/RDAP registry unlisted or unreachable")

    if domain_age_days is not None:
        if domain_age_days < 7:
            flags.append(f"Extremely young domain (Age: {domain_age_days} days)")
            score += 35.0
        elif domain_age_days < 30:
            flags.append(f"Recently registered domain (Age: {domain_age_days} days)")
            score += 20.0
        elif domain_age_days < 180:
            score += 5.0

    return {
        "heuristic_score": min(round(score, 1), 100.0),
        "domain_age_days": domain_age_days,
        "is_typosquat": is_typosquat or (target_candidate is not None),
        "target_candidate": target_candidate or (TARGET_WHITELIST.get(registered_domain)),
        "flags": flags
    }


if __name__ == "__main__":
    # Test suite with genuine domains + synthetic scam patterns
    test_urls = [
        "https://amazon.com",                                   # Real registered domain -> RDAP/WHOIS age
        "https://onlinesbi.sbi/portal/login.html",              # Whitelisted target
        "http://sbi.bank.com.scam-update.xyz/verify-login",     # Deceptive subdomain + bad TLD
        "https://onlinesbl.com/secure/login",                   # Typosquatting
        "http://192.168.1.1/kyc-update",                       # Raw IP address
    ]

    async def run_tests():
        for u in test_urls:
            print(f"\n==========================================")
            print(f"Scanning: {u}")
            print(f"==========================================")
            res = await inspect_heuristics(u)
            pprint.pprint(res)

    asyncio.run(run_tests())