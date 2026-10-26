# Trusted Retailer Allowlist & Domain Verification

## Overview

EcomInsights enforces a **configurable allowlist of trusted retailers** to guarantee genuine, apples-to-apples price comparisons. Untrusted shops, deceptive lookalike domains, unrelated marketplaces, and unverified third-party sellers are rejected before any price comparison or savings calculation is performed.

---

## Default Allowlist (India)

For India (`gl=in`), the system starts with **only two** verified retailers enabled by default:

| Store Code | Display Name | Verified Domain(s) | Priority | Status |
| :--- | :--- | :--- | :---: | :---: |
| `amazon` | **Amazon India** | `amazon.in` (and `*.amazon.in`) | 1 | **Enabled** |
| `flipkart` | **Flipkart** | `flipkart.com` (and `*.flipkart.com`) | 2 | **Enabled** |

All other stores (including Croma, Reliance Digital, Vijay Sales, Tata CLiQ, JioMart, and Poorvika) have their verified domains pre-configured but are **disabled by default**. They will only be included if explicitly added to the allowlist.

---

## Domain Verification & Lookalike Protection

The engine **never** trusts the displayed store name alone. It unpacks the actual destination URL (resolving Google Shopping redirect wrappers) and extracts the clean hostname to verify against the allowlist.

### Examples of Rejected Listings:

1. **Typo / Lookalike Domains:**
   - `https://amaz0n.in/...` -> **Rejected** (Lookalike typo)
   - `https://amazon-deals.in/...` -> **Rejected** (Deceptive prefix)
   - `https://fake-amazon.in/...` -> **Rejected**
   - `https://amazon.in.phishing.com/...` -> **Rejected** (Host is `phishing.com`, not `amazon.in`)
   - `https://flipkart.deals/...` -> **Rejected** (Unauthorized TLD)
   - `https://flipkart-store.com/...` -> **Rejected** (Hyphenated lookalike)

2. **Unverified Third-Party & Accessory Merchants:**
   - `https://nakedcase.in/...` -> **Rejected** (Accessory merchant / not in allowlist)
   - `https://babatools.com/...` -> **Rejected** (Repair parts shop / not in allowlist)
   - `https://techbazaar.in/...` -> **Rejected** (Unknown marketplace / not in allowlist)

3. **Authentic Allowlisted Domains (Accepted):**
   - `https://www.amazon.in/dp/B0CHX1W1XY` -> **Verified Amazon India**
   - `https://m.amazon.in/dp/B0CHX1W1XY` -> **Verified Amazon India**
   - `https://www.flipkart.com/apple-iphone-15/p/itm...` -> **Verified Flipkart**
   - `https://dl.flipkart.com/apple-iphone-15/p/itm...` -> **Verified Flipkart**

---

## How to Configure the Allowlist

### Method 1: Environment Variables (`.env`)

Set the `TRUSTED_RETAILERS` variable in your `.env` file or environment:

```env
# Default for India: Amazon India and Flipkart only
TRUSTED_RETAILERS="amazon,flipkart"

# Example: Adding Croma to the allowlist
TRUSTED_RETAILERS="amazon,flipkart,croma"

# Example: Adding Reliance Digital and Vijay Sales
TRUSTED_RETAILERS="amazon,flipkart,croma,reliance,vijaysales"
```

### Method 2: Dynamic Query Parameter (API)

The `/api/v1/search/universal` endpoint accepts an optional `trusted_retailers` query parameter:

```http
GET /api/v1/search/universal?query=iPhone+16&trusted_retailers=amazon,flipkart,croma
```

### Method 3: Programmatic Configuration in Code

The [`app.core.retailer_allowlist`](file:///c:/Users/MANJUNATH/Documents/Codex/2026-10-03/referenced-chatgpt-conversation-this-is-an/outputs/EcomInsights/backend/app/core/retailer_allowlist.py) module provides helper functions:

```python
from app.core.retailer_allowlist import (
    enable_trusted_retailer,
    disable_trusted_retailer,
    add_trusted_retailer,
    reset_trusted_retailers,
    TrustedRetailer,
)

# 1. Enable an existing pre-configured retailer:
enable_trusted_retailer("croma")

# 2. Disable a retailer:
disable_trusted_retailer("flipkart")

# 3. Add a brand new verified retailer with allowed domain suffixes:
add_trusted_retailer(
    TrustedRetailer(
        store_code="samsung",
        canonical_name="Samsung Official Store",
        emoji="📱",
        allowed_domains=["samsung.com"],
        priority=3,
        enabled=True,
        description="Samsung India official brand store (samsung.com)",
    )
)

# 4. Reset back to pristine India default (Amazon India and Flipkart only):
reset_trusted_retailers()
```

---

## Behavior When Trusted Retailers Are Missing or Fail Checks

- If SerpApi returns no verified listings from the allowlisted retailers, or if returned listings fail exact model matching or category price plausibility, the app **never fills the space with untrusted stores or fallback prices**.
- The app returns `stores: []`, `lowest_price: null`, and marks:
  - **Cheapest Store:** `"No trusted comparable listings found"`
  - **Recommendation:** `"No trusted comparable listings found for '<query>'. Listings from allowlisted trusted retailers (Amazon India, Flipkart) were either not found, failed model/variant checks, or lacked verified pricing. Untrusted and lookalike stores were excluded."`
