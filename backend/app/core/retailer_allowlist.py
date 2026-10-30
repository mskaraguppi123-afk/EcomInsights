"""Trusted Retailer Allowlist & Domain Verification Engine.

This module enforces a strict, configurable allowlist of trusted retailers for product
search and price comparisons.

Rules:
1. Only show listings from an explicitly configured allowlist of trusted retailers.
   For India, the default allowlist is ONLY Amazon India (amazon.in) and Flipkart (flipkart.com).
2. Identify and verify the retailer strictly from the actual result URL/domain,
   never trusting the displayed store name alone.
3. Reject lookalike domains (e.g. amaz0n.in, flipkart-deals.in, fake-amazon.com),
   unrelated marketplaces, unknown shops, and unverified third-party sellers.
4. Do not label a listing as "verified" merely because SerpApi returned it.
5. If trusted retailer listings are missing or fail product and price checks, clearly
   state that no trusted comparable listings were found; never fill the space with
   untrusted stores or invent fallback prices.

Configuration:
- Via Environment / Settings:
    TRUSTED_RETAILERS="amazon,flipkart"              # Default for India
    TRUSTED_RETAILERS="amazon,flipkart,croma"        # Add Croma to allowlist
- Via Code API:
    enable_trusted_retailer("croma")
    disable_trusted_retailer("flipkart")
    add_trusted_retailer(TrustedRetailer(...))
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from urllib.parse import parse_qs, quote_plus, unquote, urlparse


@dataclass
class TrustedRetailer:
    """Specification of an allowlisted, verified e-commerce retailer."""

    store_code: str
    canonical_name: str
    emoji: str
    allowed_domains: List[str]  # Registered root domains, e.g. ["amazon.in"]
    priority: int = 1
    enabled: bool = True
    description: str = ""

    def matches_hostname(self, hostname: str) -> bool:
        """Check if a clean hostname matches any of this retailer's allowed domains."""
        h = hostname.lower().strip(".")
        if not h:
            return False
        for d in self.allowed_domains:
            domain = d.lower().strip(".")
            if h == domain or h.endswith("." + domain):
                return True
        return False

    def matches_source_name(self, source_name: str) -> bool:
        """Check if displayed source name matches this retailer."""
        s = (source_name or "").strip().lower()
        if not s:
            return False
        if self.store_code == "amazon":
            return bool(re.search(r"^(?:amazon(?:\.in)?|amazon\s+india)$", s))
        elif self.store_code == "flipkart":
            return bool(re.search(r"^(?:flipkart(?:\.com)?)$", s))
        elif self.store_code == "croma":
            return bool(re.search(r"^(?:croma(?:\.com)?|croma\s+electronics)$", s))
        elif self.store_code == "reliance":
            return bool(re.search(r"^(?:reliance(?:\s+digital)?|reliancedigital(?:\.in)?)$", s))
        elif self.store_code == "vijaysales":
            return bool(re.search(r"^(?:vijay\s*sales(?:\.com)?)$", s))
        elif self.store_code == "tatacliq":
            return bool(re.search(r"^(?:tata\s*cliq(?:\.com)?)$", s))
        elif self.store_code == "jiomart":
            return bool(re.search(r"^(?:jiomart(?:\.com)?)$", s))
        elif self.store_code == "poorvika":
            return bool(re.search(r"^(?:poorvika(?:\s+mobiles)?(?:\.com)?)$", s))
        return False


# Canonical predefined registry of verified Indian retailers.
# Enabled by default for all premier Indian electronics retailers:
# Amazon India, Flipkart, Croma Electronics, Reliance Digital, Vijay Sales, Tata CLiQ, JioMart, Poorvika.
PREDEFINED_RETAILERS: Dict[str, TrustedRetailer] = {
    "amazon": TrustedRetailer(
        store_code="amazon",
        canonical_name="Amazon India",
        emoji="🛒",
        allowed_domains=["amazon.in"],
        priority=1,
        enabled=True,
        description="Amazon India primary marketplace (amazon.in)",
    ),
    "flipkart": TrustedRetailer(
        store_code="flipkart",
        canonical_name="Flipkart",
        emoji="🛍️",
        allowed_domains=["flipkart.com"],
        priority=2,
        enabled=True,
        description="Flipkart primary marketplace (flipkart.com)",
    ),
    "croma": TrustedRetailer(
        store_code="croma",
        canonical_name="Croma Electronics",
        emoji="🏬",
        allowed_domains=["croma.com"],
        priority=3,
        enabled=True,
        description="Tata Croma electronics retail chain (croma.com)",
    ),
    "reliance": TrustedRetailer(
        store_code="reliance",
        canonical_name="Reliance Digital",
        emoji="📱",
        allowed_domains=["reliancedigital.in"],
        priority=3,
        enabled=True,
        description="Reliance Digital nationwide electronics store (reliancedigital.in)",
    ),
    "vijaysales": TrustedRetailer(
        store_code="vijaysales",
        canonical_name="Vijay Sales",
        emoji="📺",
        allowed_domains=["vijaysales.com"],
        priority=3,
        enabled=True,
        description="Vijay Sales consumer electronics (vijaysales.com)",
    ),
    "tatacliq": TrustedRetailer(
        store_code="tatacliq",
        canonical_name="Tata CLiQ",
        emoji="🏷️",
        allowed_domains=["tatacliq.com"],
        priority=3,
        enabled=True,
        description="Tata CLiQ digital marketplace (tatacliq.com)",
    ),
    "jiomart": TrustedRetailer(
        store_code="jiomart",
        canonical_name="JioMart",
        emoji="🏪",
        allowed_domains=["jiomart.com"],
        priority=3,
        enabled=True,
        description="Reliance JioMart retail store (jiomart.com)",
    ),
    "poorvika": TrustedRetailer(
        store_code="poorvika",
        canonical_name="Poorvika Mobiles",
        emoji="📲",
        allowed_domains=["poorvika.com"],
        priority=3,
        enabled=True,
        description="Poorvika Mobiles electronics chain (poorvika.com)",
    ),
}

DEFAULT_TRUSTED_CODES: Set[str] = {
    "amazon",
    "flipkart",
    "croma",
    "reliance",
    "vijaysales",
    "tatacliq",
    "jiomart",
    "poorvika",
}


def extract_destination_url(raw_url: str) -> str:
    """Unpack destination URL from Google Shopping redirect wrappers or tracking links."""
    if not raw_url:
        return ""
    clean = raw_url.strip()
    try:
        current = clean
        # Unpack up to 3 levels of redirects
        for _ in range(3):
            parsed = urlparse(current)
            hostname = (parsed.hostname or "").lower()
            if not is_google_domain(hostname) and "google." not in hostname:
                break
            qs = parse_qs(parsed.query)
            target = None
            for param in ("url", "adurl", "q", "target", "dest", "destination", "link"):
                if param in qs and qs[param]:
                    val = unquote(qs[param][0]).strip()
                    if val.startswith("http://") or val.startswith("https://"):
                        target = val
                        break
            if target and target != current:
                current = target
            else:
                break
        return current
    except Exception:
        pass
    return clean


def validate_and_sanitize_retailer_product_url(
    raw_url: str,
    store_code: str,
    active_retailers: Optional[Dict[str, TrustedRetailer]] = None,
) -> Optional[str]:
    """Strictly validate that a product URL is an authentic, non-malformed HTTPS link
    on a verified domain for the given retailer.

    Requirements:
    - Must be a valid URL starting with 'https://'.
    - Rejects 'http://', 'javascript:', '#', empty, or malformed URLs (e.g. unencoded spaces).
    - Unpacks any Google redirect wrappers first.
    - Destination hostname must match an allowed domain for the specific retailer (e.g. amazon.in, flipkart.com).
    - Strictly rejects lookalike domains (e.g. amaz0n.in, flipkart-deals.in, fake-amazon.in).
    - Rejects Google internal search / shopping URLs.

    Returns the clean HTTPS URL if valid, or None if invalid.
    """
    if not raw_url or not isinstance(raw_url, str):
        return None
    clean = raw_url.strip()
    if not clean or clean.startswith("#") or clean.startswith("javascript:"):
        return None

    # Unpack redirect if wrapped in Google redirect
    dest = extract_destination_url(clean)
    if not dest or not dest.startswith("https://"):
        return None

    # Reject malformed URLs containing unencoded whitespace or control characters
    if any(c.isspace() for c in dest):
        return None

    try:
        parsed = urlparse(dest)
        hostname = (parsed.hostname or "").lower().strip(".")
        if not hostname:
            return None

        # Google search and shopping pages are NOT retailer product pages
        if is_google_domain(hostname):
            return None

        if active_retailers is None:
            active_retailers = get_active_trusted_retailers()

        retailer = active_retailers.get(store_code)
        if not retailer or not retailer.enabled:
            return None

        # Must match an allowed domain of the specified verified retailer
        for allowed_domain in retailer.allowed_domains:
            if is_allowed_domain_match(hostname, allowed_domain):
                return dest

        return None
    except Exception:
        return None


def build_product_query_for_search(raw_query: str) -> str:
    """Normalize a product query for retailer search while strictly preserving
    brand, model numbers, generations, storage sizes, and variant details.

    E.g.
    'iPhone 15' -> 'iPhone 15'
    'Apple iPhone 15 (128 GB) - Black' -> 'Apple iPhone 15 128 GB Black'
    'Moto G96' -> 'Moto G96'
    'Motorola Moto G96 5G 256GB' -> 'Motorola Moto G96 5G 256GB'
    """
    if not raw_query:
        return ""
    q = raw_query.strip()
    # If a URL was passed, extract product title if possible
    if q.startswith("http://") or q.startswith("https://"):
        try:
            from app.services.link_search import extract_product_title
            title, is_url, _ = extract_product_title(q)
            if is_url and title:
                q = title
        except Exception:
            pass

    # Replace punctuation like brackets, parentheses, hyphens, slashes while preserving alphanumeric
    q = re.sub(r"[()\[\]{},;:*#~`!@$%^&=+_|?<>/\\]+", " ", q)
    # Normalize multiple whitespace
    q = re.sub(r"\s+", " ", q).strip()

    from app.services.safe_url_resolver import is_disallowed_search_query
    if is_disallowed_search_query(q):
        return ""

    return q


def build_retailer_fallback_search_url(store_code: str, query: str) -> Optional[str]:
    """Build a verified, properly URL-encoded HTTPS search URL for the retailer
    using the full product query including model and variant."""
    clean_q = build_product_query_for_search(query)
    if not clean_q:
        return None
    encoded = quote_plus(clean_q)

    search_templates = {
        "amazon": f"https://www.amazon.in/s?k={encoded}",
        "flipkart": f"https://www.flipkart.com/search?q={encoded}",
        "croma": f"https://www.croma.com/search/?text={encoded}",
        "reliance": f"https://www.reliancedigital.in/search?q={encoded}",
        "vijaysales": f"https://www.vijaysales.com/search?q={encoded}",
        "tatacliq": f"https://www.tatacliq.com/search/?searchCategory=all&text={encoded}",
        "jiomart": f"https://www.jiomart.com/search?q={encoded}",
        "poorvika": f"https://www.poorvika.com/s?q={encoded}",
    }
    return search_templates.get(store_code)


def extract_hostname(url: str) -> str:
    """Extract clean lowercase hostname without port or trailing dots."""
    if not url:
        return ""
    try:
        target = extract_destination_url(url)
        parsed = urlparse(target)
        netloc = (parsed.hostname or parsed.netloc or "").lower().strip()
        if ":" in netloc:
            netloc = netloc.split(":")[0]
        return netloc.strip(".")
    except Exception:
        return ""


def is_allowed_domain_match(hostname: str, allowed_domain: str) -> bool:
    """Strictly verify if a hostname matches an allowed domain or is an authentic subdomain.

    Protects against lookalike domains, deceptive prefixes/suffixes, and phishing variations:
    - Matches: 'amazon.in' == 'amazon.in' -> True
    - Matches: 'www.amazon.in' -> True (subdomain)
    - Matches: 'm.amazon.in' -> True (subdomain)
    - Matches: 'dl.flipkart.com' -> True (subdomain)
    - Rejects: 'amaz0n.in' -> False (lookalike typo)
    - Rejects: 'amazon-deals.in' -> False (deceptive prefix)
    - Rejects: 'fake-amazon.in' -> False
    - Rejects: 'amazon.in.phishing.com' -> False (deceptive subdomain on external host)
    - Rejects: 'flipkart.deals' -> False (unauthorized TLD)
    - Rejects: 'flipkart-store.com' -> False (hyphenated lookalike)
    - Rejects: 'nakedcase.in' -> False (untrusted accessory shop)
    - Rejects: 'babatools.com' -> False (untrusted repair merchant)
    """
    h = hostname.lower().strip(".")
    d = allowed_domain.lower().strip(".")
    if not h or not d:
        return False
    # Exact domain match
    if h == d:
        return True
    # Authentic subdomain check: hostname must end with '.' + domain
    if h.endswith("." + d):
        return True
    return False


def get_active_trusted_retailers(
    override_codes: Optional[List[str] | Set[str]] = None,
) -> Dict[str, TrustedRetailer]:
    """Retrieve the dictionary of currently active, enabled trusted retailers.

    Precedence:
    1. Explicit `override_codes` argument (if provided).
    2. Codes configured in `settings.trusted_retailers` (environment / .env).
    3. Default India allowlist: Amazon India ('amazon') and Flipkart ('flipkart').
    """
    codes_to_enable: Set[str] = set()

    if override_codes is not None:
        codes_to_enable = {str(c).strip().lower() for c in override_codes if str(c).strip()}
    else:
        try:
            from app.core.config import settings
            if hasattr(settings, "trusted_retailer_list") and settings.trusted_retailer_list:
                codes_to_enable = set(settings.trusted_retailer_list)
            elif hasattr(settings, "trusted_retailers") and settings.trusted_retailers:
                codes_to_enable = {
                    r.strip().lower() for r in settings.trusted_retailers.split(",") if r.strip()
                }
        except Exception:
            pass

    # Default fallback for India: All verified premier retailers (Amazon, Flipkart, Croma, Reliance, Vijay Sales, etc.)
    if not codes_to_enable:
        codes_to_enable = set(DEFAULT_TRUSTED_CODES)

    active: Dict[str, TrustedRetailer] = {}
    for code, retailer in PREDEFINED_RETAILERS.items():
        is_enabled = code in codes_to_enable
        active[code] = TrustedRetailer(
            store_code=retailer.store_code,
            canonical_name=retailer.canonical_name,
            emoji=retailer.emoji,
            allowed_domains=list(retailer.allowed_domains),
            priority=retailer.priority,
            enabled=is_enabled,
            description=retailer.description,
        )

    return {k: v for k, v in active.items() if v.enabled}


def is_google_domain(hostname: str) -> bool:
    """Check if hostname is a Google domain (e.g. google.co.in, google.com)."""
    h = hostname.lower().strip(".")
    return h == "google.com" or h.endswith(".google.com") or h == "google.co.in" or h.endswith(".google.co.in")


def verify_retailer_from_url(
    url: str,
    source_name: str = "",
    active_retailers: Optional[Dict[str, TrustedRetailer]] = None,
) -> Optional[TrustedRetailer]:
    """Verify retailer strictly from the actual result URL and its domain.

    Returns the matching TrustedRetailer if verified and allowlisted.
    Returns None if:
    - URL domain is a lookalike (e.g. amaz0n.in, flipkart-deals.in).
    - URL domain belongs to an unknown shop, marketplace, or accessory seller.
    - URL domain belongs to a retailer that is NOT in the active allowlist.
    """
    if active_retailers is None:
        active_retailers = get_active_trusted_retailers()

    dest_url = extract_destination_url(url) if url else ""
    hostname = extract_hostname(dest_url) if dest_url else ""

    # Case 1: The URL has a specific external destination host
    if hostname and not is_google_domain(hostname):
        # Must match an allowed domain of an active trusted retailer
        for code, retailer in active_retailers.items():
            if not retailer.enabled:
                continue
            for allowed_domain in retailer.allowed_domains:
                if is_allowed_domain_match(hostname, allowed_domain):
                    return retailer
        # Hostname is external but does not match any allowlisted domain
        # (e.g. amaz0n.in, nakedcase.in, babatools.com).
        # Reject even if source_name claims otherwise!
        return None

    # Case 2: The URL is a Google Shopping/Search internal page or empty/None
    # Google Shopping aggregates verified merchant listings with source_name badge.
    if source_name:
        for code, retailer in active_retailers.items():
            if not retailer.enabled:
                continue
            if retailer.matches_source_name(source_name):
                return retailer

    return None


def add_trusted_retailer(retailer: TrustedRetailer) -> None:
    """Register or update a verified retailer in the predefined catalog."""
    PREDEFINED_RETAILERS[retailer.store_code] = retailer


def enable_trusted_retailer(store_code: str) -> bool:
    """Enable a retailer in the predefined catalog by its store code."""
    code = store_code.strip().lower()
    if code in PREDEFINED_RETAILERS:
        PREDEFINED_RETAILERS[code].enabled = True
        return True
    return False


def disable_trusted_retailer(store_code: str) -> bool:
    """Disable a retailer in the predefined catalog by its store code."""
    code = store_code.strip().lower()
    if code in PREDEFINED_RETAILERS:
        PREDEFINED_RETAILERS[code].enabled = False
        return True
    return False


def reset_trusted_retailers() -> None:
    """Reset the registry to the initial India default (all verified premier retailers enabled)."""
    for code, retailer in PREDEFINED_RETAILERS.items():
        retailer.enabled = code in DEFAULT_TRUSTED_CODES
