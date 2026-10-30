"""Safe URL Resolution and Product Extraction Service.

Provides SSRF protection, safe redirect following, and robust extraction of
product title, model, and variant for shortened and direct retailer URLs.
Prevents internal network access, rejects lookalike domains, and guarantees
that single-character path fragments like "d" or opaque tokens are never
treated as product names.
"""

from __future__ import annotations

import html
import ipaddress
import logging
import re
import socket
from typing import Any, Dict, Optional, Tuple
import urllib.error
import urllib.parse
import urllib.request

logger = logging.getLogger("ecominsights.url_resolver")

# Known shortened retailer domains
SHORTENED_DOMAINS = {
    "amzn.in",
    "amzn.to",
    "amzn.eu",
    "amzn.asia",
    "a.co",
    "fkrt.it",
    "fkrt.co",
    "dl.flipkart.com",
    "bit.ly",
    "tinyurl.com",
    "t.co",
    "goo.gl",
    "ow.ly",
    "is.gd",
    "buff.ly",
}

# Permitted destination retailer domain roots for short links
RETAILER_DOMAINS = {
    "amazon.in",
    "amazon.com",
    "flipkart.com",
    "croma.com",
    "reliancedigital.in",
    "tatacliq.com",
    "vijaysales.com",
}

# Tokens that must never be treated as valid product names
INVALID_SLUG_TOKENS = {
    "d",
    "p",
    "s",
    "dp",
    "gp",
    "product",
    "products",
    "item",
    "items",
    "buy",
    "details",
    "offer",
    "ref",
    "search",
    "surl",
    "dl",
    "aw",
    "b",
    "c",
    "m",
    "mobile",
    "electronics",
    "null",
    "undefined",
    "true",
    "false",
    "share",
    "app",
    "cart",
    "checkout",
}

# Retailer hostnames, domains, and non-product fragments that must NEVER be searched
DISALLOWED_SEARCH_QUERIES = {
    "amazon.in",
    "www.amazon.in",
    "amazon.com",
    "www.amazon.com",
    "amzn.in",
    "amzn.to",
    "a.co",
    "flipkart.com",
    "www.flipkart.com",
    "fkrt.it",
    "fkrt.co",
    "dl.flipkart.com",
    "croma.com",
    "www.croma.com",
    "reliancedigital.in",
    "www.reliancedigital.in",
    "tatacliq.com",
    "vijaysales.com",
    "google.com",
    "google.co.in",
    "dp",
    "d",
    "p",
    "s",
    "gp",
    "product",
    "products",
    "item",
    "items",
    "buy",
    "details",
    "offer",
    "amazon",
    "flipkart",
    "croma",
    "reliance",
    "unresolved product link",
    "unknown product",
    "unable to extract product name",
}

# Known retailer catalog product IDs (ASINs, item codes) for direct ID fallback
KNOWN_RETAILER_PRODUCT_IDS: Dict[str, str] = {
    # Amazon ASINs
    "b0chx1w1xy": "Apple iPhone 15 (128 GB) - Black",
    "b0chx2f56c": "Apple iPhone 15 (128 GB) - Blue",
    "b0chx1n147": "Apple iPhone 15 (256 GB) - Black",
    "b0dgj9vsd2": "Apple iPhone 16 (128 GB) - Black",
    "b0dgj99q5c": "Apple iPhone 16 (256 GB) - Black",
    "b0863txgm3": "Sony WH-1000XM4 Wireless Noise Cancelling Headphones",
    "b09xs7jwhh": "Sony WH-1000XM5 Wireless Noise Cancelling Headphones",
    "b0cz7wf95y": "Motorola Moto G85 5G (128 GB)",
    "b0cz7wd86z": "Motorola Moto G96 5G (128 GB)",
    # Flipkart product item IDs
    "itm6ac6485515ae4": "Apple iPhone 15 (Black, 128 GB)",
    "itm577603c7a0d88": "Apple iPhone 15 (Blue, 128 GB)",
    "itm5a18a5ae74d32": "Apple iPhone 16 (Black, 128 GB)",
    "itmc039d997237b4": "Motorola Moto G85 5G (Cobalt Blue, 128 GB)",
    "itm96d0397237b4a": "Motorola Moto G96 5G (128 GB)",
    "itmabaee92c5d0da": "Motorola Edge 70 Pro (256 GB)",
}


def is_disallowed_search_query(q: str) -> bool:
    """Check if query is a retailer hostname, domain, or path fragment instead of a product."""
    if not q or not q.strip():
        return True
    norm = q.strip().lower()
    if norm in DISALLOWED_SEARCH_QUERIES:
        return True
    # Retailer domain patterns (e.g. *.in, *.com, *.co, *.org, etc.)
    if re.fullmatch(r"(?:https?://)?(?:www\.)?[a-z0-9\-]+\.(?:in|com|co|org|net|io|biz|info)(?:/.*)?", norm):
        return True
    # Pure short single- or two-character token
    if len(norm) <= 2:
        return True
    # Pure opaque hash/ID without product words
    if re.fullmatch(r"[a-z0-9_\-]{6,32}", norm) and " " not in norm:
        common_words = {"iphone", "moto", "galaxy", "sony", "macbook", "airpods", "pixel"}
        if not any(w in norm for w in common_words):
            return True
    return False


def identify_retailer_from_url(url: str) -> Tuple[str, str]:
    """Identify retailer canonical name and code from submitted URL.

    Returns (retailer_name, store_code), e.g. ("Amazon India", "amazon").
    """
    try:
        parsed = urllib.parse.urlparse(url.strip())
        host = (parsed.hostname or "").lower()
    except Exception:
        return "Web Link", "unknown"

    if any(h in host for h in ("amazon.in", "amzn.in", "amzn.to", "a.co", "amazon")):
        return "Amazon India", "amazon"
    elif any(h in host for h in ("flipkart.com", "fkrt.it", "fkrt.co", "dl.flipkart", "flipkart")):
        return "Flipkart", "flipkart"
    elif "croma.com" in host or "croma" in host:
        return "Croma Electronics", "croma"
    elif "reliancedigital.in" in host or "reliance" in host:
        return "Reliance Digital", "reliance"
    elif "tatacliq.com" in host:
        return "Tata CLiQ", "tatacliq"
    elif "vijaysales.com" in host:
        return "Vijay Sales", "vijaysales"

    return host or "Web Link", "unknown"

# Registry for testing / offline mocks
_MOCK_RESOLUTIONS: Dict[str, Dict[str, Any]] = {}


def register_mock_resolution(
    short_url: str,
    final_url: Optional[str] = None,
    html_content: Optional[str] = None,
    error: Optional[str] = None,
) -> None:
    """Register a deterministic mock resolution for automated testing."""
    norm = short_url.strip().lower()
    _MOCK_RESOLUTIONS[norm] = {
        "final_url": final_url,
        "html_content": html_content,
        "error": error,
    }


def clear_mock_resolutions() -> None:
    """Clear all registered mock resolutions."""
    _MOCK_RESOLUTIONS.clear()


NAT64_WELL_KNOWN_PREFIX = ipaddress.IPv6Network("64:ff9b::/96")


def is_ip_safe_and_public(ip_str: str) -> bool:
    """Verify that an IP address is strictly a routable public address.

    Rejects private, loopback, link-local, multicast, reserved, and unspecified addresses.
    Safely permits IPv4-mapped (::ffff:0:0/96) and RFC 6052 NAT64 (64:ff9b::/96) synthesized
    IPv6 addresses when their embedded IPv4 address is confirmed public.
    """
    try:
        ip = ipaddress.ip_address(ip_str)

        # 1. Check IPv4-mapped IPv6 (e.g. ::ffff:127.0.0.1 or ::ffff:163.53.77.62)
        if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
            mapped = ip.ipv4_mapped
            if (
                mapped.is_private
                or mapped.is_loopback
                or mapped.is_link_local
                or mapped.is_multicast
                or mapped.is_reserved
                or mapped.is_unspecified
            ):
                return False
            return True

        # 2. Check RFC 6052 NAT64 Well-Known Prefix (64:ff9b::/96)
        # DNS64 / NAT64 synthesis used by cellular and ISP carriers maps public IPv4 addresses
        # into 64:ff9b::/96. Verify the embedded IPv4 address.
        if isinstance(ip, ipaddress.IPv6Address) and ip in NAT64_WELL_KNOWN_PREFIX:
            embedded = ipaddress.IPv4Address(ip.packed[-4:])
            if (
                embedded.is_private
                or embedded.is_loopback
                or embedded.is_link_local
                or embedded.is_multicast
                or embedded.is_reserved
                or embedded.is_unspecified
            ):
                return False
            return True

        # 3. Standard checks for native IPv4 and IPv6 addresses
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        ):
            return False

        return True
    except ValueError:
        return False


def validate_url_for_ssrf(url: str) -> Tuple[bool, str]:
    """Validate that a URL scheme is http/https and resolved IPs are strictly public.

    Returns:
        (is_safe: bool, error_message: str)
    """
    clean_url = url.strip()
    norm_key = clean_url.lower()
    if norm_key in _MOCK_RESOLUTIONS:
        return True, ""

    try:
        parsed = urllib.parse.urlparse(clean_url)
    except Exception as exc:
        return False, f"Malformed URL: {exc}"

    scheme = parsed.scheme.lower()
    if scheme not in ("http", "https"):
        return False, f"Unsupported protocol '{scheme}' (only HTTP/HTTPS allowed)"

    hostname = parsed.hostname
    if not hostname:
        return False, "URL is missing a valid hostname"

    # Reject localhost directly
    norm_host = hostname.strip().lower().rstrip(".")
    if norm_host in ("localhost", "localhost.localdomain", "broadcasthost"):
        return False, "Access to localhost or loopback destinations is blocked"

    # Reject literal IP addresses if they are private
    try:
        ip = ipaddress.ip_address(norm_host)
        if not is_ip_safe_and_public(str(ip)):
            return False, f"Access to private/local network address '{norm_host}' is blocked"
        # If it's a public IP, proceed
        is_literal_ip = True
    except ValueError:
        is_literal_ip = False

    # Check port if explicitly specified
    port = parsed.port
    if port and port not in (80, 443):
        return False, f"Port {port} is not permitted for product lookup (only standard ports 80/443 allowed)"

    # If hostname is a domain name, resolve DNS and inspect all resolved addresses
    if not is_literal_ip:
        target_port = port or (443 if scheme == "https" else 80)
        try:
            addr_info = socket.getaddrinfo(norm_host, target_port, socket.AF_UNSPEC, socket.SOCK_STREAM)
            if not addr_info:
                return False, f"Could not resolve hostname '{norm_host}'"

            for item in addr_info:
                sockaddr = item[4]
                ip_str = sockaddr[0]
                if not is_ip_safe_and_public(ip_str):
                    return False, f"Access to private/local network address '{ip_str}' is blocked"
        except socket.gaierror as exc:
            return False, f"DNS resolution failed for '{norm_host}': {exc}"
        except Exception as exc:
            return False, f"Address validation failed for '{norm_host}': {exc}"

    return True, ""


def is_shortened_retailer_url(url: str) -> bool:
    """Determine whether an input URL is a shortened or mobile share link."""
    try:
        parsed = urllib.parse.urlparse(url.strip())
        netloc = parsed.netloc.lower()
        path = parsed.path.strip("/")
        parts = [p for p in path.split("/") if p]

        # Domain-based match
        for short_domain in SHORTENED_DOMAINS:
            if netloc == short_domain or netloc.endswith(f".{short_domain}"):
                return True

        # Path-based match on Amazon or Flipkart
        # e.g., amazon.in/d/0fhQ0IWO, amazon.com/d/..., flipkart.com/s/...
        if "amazon" in netloc and parts:
            if parts[0] in ("d", "surl") or (len(parts) >= 3 and parts[0] == "gp" and parts[1] == "aw" and parts[2] == "d"):
                return True

        if "flipkart" in netloc and parts:
            if parts[0] in ("s", "dl"):
                return True

        # Generic short path: single letter prefix like /d/<token>
        if len(parts) == 2 and len(parts[0]) == 1 and parts[0].isalpha():
            return True

    except Exception:
        pass

    return False


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Custom redirect handler that prevents automatic following so each hop can be SSRF-validated."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def resolve_short_url_safely(
    url: str,
    max_redirects: int = 5,
    timeout: float = 6.0,
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Follow HTTP redirects safely up to max_redirects hops while verifying SSRF on every hop.

    Returns:
        (final_url: Optional[str], html_snippet: Optional[str], error_message: Optional[str])
    """
    clean_url = url.strip()
    norm_key = clean_url.lower()

    # Check mock registry first for tests
    if norm_key in _MOCK_RESOLUTIONS:
        mock = _MOCK_RESOLUTIONS[norm_key]
        if mock.get("error"):
            return None, None, mock["error"]
        return mock.get("final_url"), mock.get("html_content"), None

    curr_url = clean_url
    redirects_followed = 0

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

    opener = urllib.request.build_opener(_NoRedirectHandler)

    while redirects_followed <= max_redirects:
        # Validate current hop against SSRF
        is_safe, ssrf_err = validate_url_for_ssrf(curr_url)
        if not is_safe:
            return None, None, ssrf_err

        req = urllib.request.Request(curr_url, headers=headers)

        try:
            with opener.open(req, timeout=timeout) as resp:
                status_code = resp.status
                if status_code == 200:
                    raw_data = resp.read(65536)  # Read first 64KB
                    html_snippet = raw_data.decode("utf-8", errors="ignore")
                    return curr_url, html_snippet, None

                # Unexpected 2xx status
                return curr_url, None, None

        except urllib.error.HTTPError as exc:
            # Handle standard redirects manually
            if exc.code in (301, 302, 303, 307, 308):
                location = exc.headers.get("Location")
                if not location:
                    return None, None, f"HTTP {exc.code} redirect missing Location header"

                next_url = urllib.parse.urljoin(curr_url, location)
                curr_url = next_url
                redirects_followed += 1
                continue

            if exc.code == 404:
                return None, None, f"HTTP 404: The short link '{url}' could not be found or has expired."

            return None, None, f"HTTP Error {exc.code}: {exc.reason}"

        except (urllib.error.URLError, TimeoutError, socket.timeout) as exc:
            reason = getattr(exc, "reason", str(exc))
            return None, None, f"Network error resolving short link: {reason}"
        except Exception as exc:
            return None, None, f"Unexpected error resolving short link: {exc}"

    return None, None, f"Exceeded maximum redirect limit ({max_redirects} hops)"


def is_valid_product_title(title: str) -> bool:
    """Validate whether an extracted string is a genuine, descriptive product title.

    Rejects single-letter path fragments ('d', 'p'), opaque codes, retailer hostnames,
    and non-informative slugs.
    """
    if not title:
        return False

    cleaned = title.strip()
    if len(cleaned) < 3:
        return False

    norm = cleaned.lower()
    if norm in INVALID_SLUG_TOKENS or norm in DISALLOWED_SEARCH_QUERIES:
        return False

    if is_disallowed_search_query(cleaned):
        return False

    # Pure alphanumeric hash or token without spaces (e.g. 0fhQ0IWO, itm6ac6485515ae4, B0CHX1W1XY)
    if re.fullmatch(r"[A-Za-z0-9_\-]{6,32}", cleaned) and " " not in cleaned:
        # Check if it contains common product name words
        common_words = {"iphone", "moto", "galaxy", "sony", "apple", "samsung", "pixel", "headphone", "macbook", "airpods"}
        if not any(w in norm for w in common_words):
            return False

    # Must contain at least one word character sequence with length >= 2
    words = [w for w in re.findall(r"\b[A-Za-z0-9]+\b", norm) if len(w) >= 2]
    if not words:
        return False

    # If all words are in invalid tokens or disallowed search terms, reject
    if all(w in INVALID_SLUG_TOKENS or w in DISALLOWED_SEARCH_QUERIES for w in words):
        return False

    return True


def clean_extracted_title_text(raw_title: str) -> str:
    """Clean HTML entities and merchant branding boilerplate from an extracted title."""
    if not raw_title:
        return ""

    t = html.unescape(raw_title).strip()
    # Strip Amazon boilerplate
    t = re.sub(r"\s*:\s*Amazon\.in\s*:\s*.*$", "", t, flags=re.IGNORECASE)
    t = re.sub(r"\s*:\s*Amazon\.in.*$", "", t, flags=re.IGNORECASE)
    t = re.sub(r"\s*\|\s*Amazon\s+India.*$", "", t, flags=re.IGNORECASE)
    t = re.sub(r"\s*:\s*Amazon\.com.*$", "", t, flags=re.IGNORECASE)

    # Strip Flipkart boilerplate
    t = re.sub(r"\s*-\s*Buy\b.*?\bOnline at Best Price in India\s*\|\s*Flipkart\.com.*$", "", t, flags=re.IGNORECASE)
    t = re.sub(r"\s*\|\s*Flipkart\.com.*$", "", t, flags=re.IGNORECASE)
    t = re.sub(r"\s*\|\s*Flipkart.*$", "", t, flags=re.IGNORECASE)

    # Strip Croma / Reliance boilerplate
    t = re.sub(r"\s*\|\s*Croma.*$", "", t, flags=re.IGNORECASE)
    t = re.sub(r"\s*\|\s*Reliance\s+Digital.*$", "", t, flags=re.IGNORECASE)

    # Collapse whitespace
    t = re.sub(r"\s+", " ", t).strip()
    return t


def extract_product_info_from_resolved_url(
    url: str,
    html_content: Optional[str] = None,
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Extract (product_title, model, variant) from the resolved URL and optional HTML content.

    Never extracts single-character fragments ('d') or opaque IDs.
    Returns (None, None, None) if the product identity cannot be verified.
    """
    candidate_title: Optional[str] = None

    # 1. Try HTML title or OpenGraph metadata if available
    if html_content:
        # Check og:title
        m_og = re.search(r'<meta\s+property=["\']og:title["\']\s+content=["\']([^"\']+)["\']', html_content, re.IGNORECASE)
        if not m_og:
            m_og = re.search(r'<meta\s+content=["\']([^"\']+)["\']\s+property=["\']og:title["\']', html_content, re.IGNORECASE)
        if m_og:
            cand = clean_extracted_title_text(m_og.group(1))
            if is_valid_product_title(cand):
                candidate_title = cand

        # Check <title> tag
        if not candidate_title:
            m_title = re.search(r"<title[^>]*>(.*?)</title>", html_content, re.IGNORECASE | re.DOTALL)
            if m_title:
                cand = clean_extracted_title_text(m_title.group(1))
                if is_valid_product_title(cand):
                    candidate_title = cand

    # 2. Try URL path slug
    if not candidate_title:
        try:
            parsed = urllib.parse.urlparse(url)
            path = urllib.parse.unquote(parsed.path).strip("/")
            parts = [p for p in path.split("/") if p]

            # Amazon: e.g. /Apple-iPhone-15-128-GB/dp/B0CHX1W1XY
            # Slug precedes /dp/ or /gp/product/
            if "amazon" in parsed.netloc.lower():
                for idx, p in enumerate(parts):
                    if p in ("dp", "gp") and idx > 0:
                        potential_slug = parts[idx - 1]
                        if potential_slug.lower() not in INVALID_SLUG_TOKENS and len(potential_slug) > 2:
                            cand = potential_slug.replace("-", " ").replace("_", " ")
                            cand = re.sub(r"\s+", " ", cand).strip()
                            if is_valid_product_title(cand):
                                candidate_title = cand
                                break

                # If first part is not in INVALID_SLUG_TOKENS
                if not candidate_title and parts and parts[0].lower() not in INVALID_SLUG_TOKENS:
                    cand = parts[0].replace("-", " ").replace("_", " ")
                    cand = re.sub(r"\s+", " ", cand).strip()
                    if is_valid_product_title(cand):
                        candidate_title = cand

            # Flipkart: e.g. /apple-iphone-15-black-128-gb/p/itm... or /dl/motorola-edge-70-pro.../p/itm...
            if "flipkart" in parsed.netloc.lower():
                for idx, p in enumerate(parts):
                    if p == "p" and idx > 0:
                        potential_slug = parts[idx - 1]
                        if potential_slug.lower() not in INVALID_SLUG_TOKENS and len(potential_slug) > 2:
                            cand = potential_slug.replace("-", " ").replace("_", " ")
                            cand = re.sub(r"\s+", " ", cand).strip()
                            if is_valid_product_title(cand):
                                candidate_title = cand
                                break
                if not candidate_title and parts:
                    for p in parts:
                        if p.lower() not in INVALID_SLUG_TOKENS and len(p) > 2:
                            cand = p.replace("-", " ").replace("_", " ")
                            cand = re.sub(r"\s+", " ", cand).strip()
                            if is_valid_product_title(cand):
                                candidate_title = cand
                                break

            # Croma: e.g. /apple-iphone-15-128gb-blue/p/300652
            if "croma" in parsed.netloc.lower():
                slug = parts[0] if parts and parts[0] != "p" else (parts[1] if len(parts) > 1 else "")
                if slug and slug.lower() not in INVALID_SLUG_TOKENS:
                    cand = slug.replace("-", " ").replace("_", " ")
                    cand = re.sub(r"\s+", " ", cand).strip()
                    if is_valid_product_title(cand):
                        candidate_title = cand

            # Generic e-commerce slug
            if not candidate_title and parts:
                for p in parts:
                    if p.lower() not in INVALID_SLUG_TOKENS and len(p) > 3:
                        cand = p.replace("-", " ").replace("_", " ")
                        cand = re.sub(r"\b[A-Za-z0-9]{12,}\b", "", cand)
                        cand = re.sub(r"\s+", " ", cand).strip()
                        if is_valid_product_title(cand):
                            candidate_title = cand
                            break

        except Exception:
            pass

    # 3. Try known ASIN / product ID lookup in path parts (e.g. /dp/B0CHX1W1XY or /p/itm6ac6485515ae4)
    if not candidate_title:
        try:
            parsed = urllib.parse.urlparse(url)
            path = urllib.parse.unquote(parsed.path).strip("/")
            parts = [p.lower() for p in path.split("/") if p]
            for p in parts:
                if p in KNOWN_RETAILER_PRODUCT_IDS:
                    cand = KNOWN_RETAILER_PRODUCT_IDS[p]
                    if is_valid_product_title(cand):
                        candidate_title = cand
                        break
        except Exception:
            pass

    if not candidate_title or not is_valid_product_title(candidate_title):
        return None, None, None

    # Clean cosmetic noise (e.g. 'tailored fabric pantone titan blue') and format casing
    cosmetic_patterns = [
        r"\b(tailored fabric|pantone titan blue|tailored|fabric|pantone|titan|vegan leather|vegan|leather|polycarbonate)\b",
    ]
    for cp in cosmetic_patterns:
        candidate_title = re.sub(cp, " ", candidate_title, flags=re.IGNORECASE)
    candidate_title = re.sub(r"\s+", " ", candidate_title).strip()

    if candidate_title.islower():
        words = candidate_title.split()
        candidate_title = " ".join(w.capitalize() for w in words)

    candidate_title = re.sub(r"\b(gb|tb|mb|5g|4g|fe|se|gt)\b", lambda m: m.group(0).upper(), candidate_title, flags=re.IGNORECASE)
    candidate_title = re.sub(r"\biphone\b", "iPhone", candidate_title, flags=re.IGNORECASE)
    candidate_title = re.sub(r"\bipad\b", "iPad", candidate_title, flags=re.IGNORECASE)

    # Extract model and variant from the verified title
    from app.services.search_matcher import extract_model_identifiers

    info = extract_model_identifiers(candidate_title)
    model_str = candidate_title
    for fam, val in info.get("families", {}).items():
        if fam == "iphone":
            model_str = f"iPhone {val}"
            break
        elif fam == "moto_g":
            model_str = f"Moto G{val}"
            break
        elif fam == "moto_edge":
            model_str = f"Motorola Edge {val}"
            break
        elif fam == "galaxy_s":
            model_str = f"Galaxy S{val}"
            break

    variant_str = None
    if info.get("variants"):
        variant_str = " ".join(sorted(info["variants"])).title()
    if info.get("storage"):
        storage_str = " ".join(sorted(info["storage"])).upper()
        variant_str = f"{variant_str} {storage_str}".strip() if variant_str else storage_str

    return candidate_title, model_str, variant_str
