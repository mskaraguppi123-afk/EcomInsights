"""Model-aware product search and normalization service.

Normalizes harmless differences (capitalization, extra spaces, punctuation)
while strictly preserving and validating meaningful differences (model numbers,
generations, storage sizes, variants).
Ranks exact matches ahead of partial matches and excludes results with conflicting
model numbers or generations.
"""

from decimal import Decimal
import re
from typing import Any, Optional, Sequence, Tuple


def normalize_search_text(text: str) -> str:
    """Normalize harmless differences: lowercasing, extra spaces, and common punctuation."""
    if not text:
        return ""
    t = text.lower().strip()
    # Normalize punctuation between words to spaces, but keep alphanumeric groupings
    t = re.sub(r"[\-_/+,|:;*#]", " ", t)
    # Remove symbols that don't carry model information
    t = re.sub(r"[()\[\]{}'\"`~!?@$%^&=<>]", " ", t)
    # Normalize multiple whitespaces
    return re.sub(r"\s+", " ", t).strip()


def extract_model_identifiers(text: str) -> dict[str, Any]:
    """Extract model numbers, generations, family designations, storage sizes, and variants."""
    norm = normalize_search_text(text)
    tokens = [tok for tok in norm.split() if tok]
    token_set = set(tokens)

    # Standalone numbers (e.g. "16", "18", "15", "10", "9")
    numbers = set(re.findall(r"\b\d+\b", norm))

    # Alphanumeric model codes (e.g. "1000xm4", "1000xm5", "s24", "s23", "m1", "m2", "m3", "128gb", "256gb")
    model_codes = set(re.findall(r"\b(?:[a-z]+\d+|\d+[a-z]+[a-z0-9]*)\b", norm))

    # Product line families with specific model numbers
    families: dict[str, str] = {}
    family_patterns = [
        (r"\biphone\s+(\d+|se|x|xs|xr)\b", "iphone"),
        (r"\b(?:galaxy\s+)?s\s*(\d+)\b", "galaxy_s"),
        (r"\b(?:galaxy\s+)?z\s*(fold|flip)\s*(\d+)?\b", "galaxy_z"),
        (r"\bpixel\s+(\d+[a-z]?)\b", "pixel"),
        (r"\boneplus\s+(\d+[a-z]?)\b", "oneplus"),
        (r"\bipad\s+(mini|air|pro|\d+)\b", "ipad"),
        (r"\bwh\s*(\d+[a-z0-9]+)\b", "sony_wh"),
        (r"\bwf\s*(\d+[a-z0-9]+)\b", "sony_wf"),
    ]
    for pattern, fam_name in family_patterns:
        m = re.search(pattern, norm)
        if m:
            families[fam_name] = "".join(m.groups(default="")).replace(" ", "")

    # Generations (e.g. "10th gen", "9th gen", "gen 1", "gen 2", "m1", "m2", "m3")
    gen_match = re.search(r"\b(\d+(?:st|nd|rd|th)\s+gen|gen\s+\d+|m[1-4])\b", norm)
    generation = gen_match.group(1).replace(" ", "") if gen_match else None

    # Variants (e.g. "pro max", "pro", "plus", "mini", "ultra", "fe", "air", "max")
    variants = set()
    for v in ["pro max", "pro", "plus", "mini", "ultra", "fe", "air", "max"]:
        if re.search(rf"\b{v}\b", norm):
            variants.add(v)

    # Storage specs (e.g. "128gb", "256gb", "512gb", "1tb", "64gb")
    storage_matches = set(re.findall(r"\b(\d+\s*(?:gb|tb))\b", norm))
    storage = {s.replace(" ", "") for s in storage_matches}

    return {
        "raw": text,
        "normalized": norm,
        "tokens": tokens,
        "token_set": token_set,
        "numbers": numbers,
        "model_codes": model_codes,
        "families": families,
        "generation": generation,
        "variants": variants,
        "storage": storage,
    }


def match_product(query: str, candidate_name: str) -> Tuple[bool, int, str]:
    """Determine whether a candidate product matches a search query.

    Returns:
        (is_match: bool, score: int, match_reason: str)
        score is from 0 (excluded / no match) to 100 (exact match).
    """
    if not query or not query.strip():
        return True, 50, "Empty query (show all)"

    q_info = extract_model_identifiers(query)
    c_info = extract_model_identifiers(candidate_name)

    # 1. Family Model Conflict (e.g. iPhone 16 vs iPhone 18)
    # A query for iPhone 16 MUST NOT match iPhone 18
    for fam, q_val in q_info["families"].items():
        if fam in c_info["families"]:
            c_val = c_info["families"][fam]
            if q_val != c_val:
                return False, 0, f"Conflicting {fam} model: '{q_val}' != '{c_val}'"

    # 2. Standalone Numbers Conflict
    # If the query specifies a model number like "16", any candidate in the same brand/type
    # that has a differing model number like "18" or "15" must be excluded.
    if q_info["numbers"]:
        # If query has numbers, candidate must contain those numbers if candidate has numbers
        missing_numbers = q_info["numbers"] - c_info["numbers"]
        if missing_numbers:
            # Check if this missing number is a core model number (like 16, 18, 15)
            # If candidate has other numbers in place of the query numbers, it's a conflict
            if c_info["numbers"]:
                return False, 0, f"Conflicting numeric model identifier (expected {q_info['numbers']}, candidate has {c_info['numbers']})"
            else:
                return False, 0, f"Candidate lacks required model number {missing_numbers}"

    # 3. Model Code Conflict (e.g. 1000xm4 vs 1000xm5)
    if q_info["model_codes"]:
        missing_codes = q_info["model_codes"] - c_info["model_codes"]
        if missing_codes:
            # Check if candidate has differing model codes with same prefix (e.g. 1000xm5)
            if c_info["model_codes"]:
                return False, 0, f"Conflicting model code: missing {missing_codes}"

    # 4. Generation Conflict (e.g. 10th gen vs 9th gen, m2 vs m1)
    if q_info["generation"] and c_info["generation"]:
        if q_info["generation"] != c_info["generation"]:
            return False, 0, f"Conflicting generation: {q_info['generation']} != {c_info['generation']}"

    # 5. Storage Conflict (if query specifically asked for 128gb and candidate has 256gb)
    if q_info["storage"] and c_info["storage"]:
        if not q_info["storage"].intersection(c_info["storage"]):
            return False, 0, f"Conflicting storage: {q_info['storage']} != {c_info['storage']}"

    # 6. Variant Conflict (e.g. query specifies "pro" but candidate is base model, or vice-versa)
    if q_info["variants"]:
        # If user explicitly searched for a variant (e.g. "pro max"), candidate must match
        if not q_info["variants"].intersection(c_info["variants"]):
            return False, 0, f"Missing requested variant: {q_info['variants']}"

    # 7. Token Overlap & Scoring
    q_tokens = q_info["token_set"]
    c_tokens = c_info["token_set"]

    # Filter out common filler words for overlap calculation
    fillers = {"the", "and", "with", "for", "in", "by", "of", "to", "a", "an", "apple"}
    significant_q_tokens = {t for t in q_tokens if t not in fillers}
    significant_c_tokens = {t for t in c_tokens if t not in fillers}

    if not significant_q_tokens:
        significant_q_tokens = q_tokens
        significant_c_tokens = c_tokens

    # Check exact match
    if q_info["normalized"] == c_info["normalized"]:
        return True, 100, "Exact match"

    # Check normalized core model exact match
    # e.g., query "iphone 16" and candidate "apple iphone 16"
    if significant_q_tokens == significant_c_tokens:
        return True, 98, "Exact token match"

    # All significant query tokens present in candidate (e.g. "iphone 16" in "apple iphone 16 128gb")
    if significant_q_tokens.issubset(significant_c_tokens):
        # If candidate has extra variants not in query (e.g. query "iphone 16" vs candidate "iphone 16 pro max"),
        # rank it lower than exact base model
        extra_variants = c_info["variants"] - q_info["variants"]
        if extra_variants:
            return True, 70, f"Model matches with extra variant: {extra_variants}"
        return True, 90, "All query tokens present"

    # Partial overlap
    overlap = significant_q_tokens.intersection(significant_c_tokens)
    ratio = len(overlap) / len(significant_q_tokens) if significant_q_tokens else 0.0

    if ratio >= 0.75:
        return True, int(ratio * 75), "Strong partial match"
    elif ratio >= 0.5 and len(significant_q_tokens) > 2:
        return True, int(ratio * 50), "Partial match"

    return False, 0, f"Insufficient token overlap (ratio: {ratio:.2f})"


def rank_and_filter_products(
    query: Optional[str],
    products: Sequence[Any],
    name_attr: str = "name",
) -> list[Any]:
    """Filter and rank a list of product objects according to query relevance.

    Exact matches are ranked first, followed by spec/variant matches and partial matches.
    Conflicting model numbers (e.g. iPhone 18 when searching for iPhone 16) are strictly excluded.
    """
    if not query or not query.strip():
        return list(products)

    scored_items: list[Tuple[int, Any]] = []
    for item in products:
        name = getattr(item, name_attr, "") if hasattr(item, name_attr) else str(item.get(name_attr, ""))
        is_match, score, _ = match_product(query, name)
        if is_match and score > 0:
            scored_items.append((score, item))

    # Sort primarily by score descending, secondarily by product name
    scored_items.sort(
        key=lambda pair: (
            -pair[0],
            getattr(pair[1], name_attr, "") if hasattr(pair[1], name_attr) else str(pair[1].get(name_attr, "")),
        )
    )
    return [item for _, item in scored_items]
