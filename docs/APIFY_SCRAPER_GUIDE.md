# Apify Web Scraping & MCP Integration Guide

This guide explains how to use **Apify** web scraping actors to extract real e-commerce pricing, product availability, ratings, and arbitrage deals for **EcomInsights**, as well as how to configure the **Apify Model Context Protocol (MCP)** server.

---

## Architecture Overview

```text
┌────────────────┐       ┌──────────────────────┐       ┌────────────────────────┐
│  React + Vite  │ ───▶  │   FastAPI Backend    │ ───▶  │   Apify Cloud Platform │
│   Dashboard    │       │ (ApifyScraperService)│       │ (junglee/amazon-crawl) │
└────────────────┘       └──────────────────────┘       └────────────────────────┘
                                    │                               │
                                    ▼                               ▼
                         ┌─────────────────────┐        ┌───────────────────────┐
                         │ ecominsights.db     │        │ Live Prices, Ratings, │
                         │ (Product & History) │        │ In-Stock & Direct URLs│
                         └─────────────────────┘        └───────────────────────┘
```

The system provides a two-layer scraping approach:
1. **Live Cloud Crawling:** When `APIFY_API_TOKEN` is configured, calls Apify actors to crawl Amazon/e-commerce listings directly in real time.
2. **Offline Simulation Mode:** When running offline or without an API key, automatically generates realistic price variations so full demonstration, viva presentation, and tests continue running seamlessly without network latency.

---

## 1. Quick Setup: Enabling Live Apify Scraping

1. Create a free account at [console.apify.com](https://console.apify.com/) (Apify provides **$5/month free credit** every month, enough for thousands of product crawls).
2. Go to **Settings > Integrations** and copy your **Personal API Token**.
3. In your `.env` file (or `backend/.env`), set:

```bash
APIFY_API_TOKEN=your_apify_api_token_here
APIFY_AMAZON_ACTOR=junglee/amazon-crawler
APIFY_TIMEOUT_SECS=60
```

4. Restart your FastAPI backend server. The UI status badge will automatically switch to `🕷️ Apify Cloud: Active`.

---

## 2. Using Apify Scraping via the Web UI

1. Open the EcomInsights web app at `http://localhost:5173`.
2. In the **Link-Based & Universal Search** card:
   - Type a product name (e.g. `Sony WH-1000XM5` or `Apple AirPods Pro`) or paste an Amazon product link.
   - Click the green **🕷️ Live Scrape (Apify)** button.
3. The Apify crawler will fetch the listings, compute arbitrage across offers, highlight the **Lowest Price**, and automatically record the timestamped price observation in the database.

---

## 3. Running Apify Scrapers from the Command Line (CLI)

A dedicated CLI utility is available in `backend/app/scripts/scrape_apify.py`:

### Check Connection & Token Status
```powershell
python backend\app\scripts\scrape_apify.py --status
```

### Crawl a Product and Print Arbitrage Table
```powershell
python backend\app\scripts\scrape_apify.py --query "Sony WH-1000XM5" --store amazon
```

### Crawl and Persist Observations Directly to Database
```powershell
python backend\app\scripts\scrape_apify.py --query "Apple iPhone 16" --save
```

---

## 4. REST API Endpoints

### `GET /api/v1/apify/status`
Checks Apify token configuration, connectivity, username, and account plan.

**Sample Response:**
```json
{
  "configured": true,
  "connected": true,
  "username": "developer",
  "plan": "Free / Standard",
  "message": "Connected to Apify as developer (Free / Standard)."
}
```

### `POST /api/v1/apify/scrape`
Executes an Apify crawl and returns extracted product quotes and arbitrage savings.

**Request Payload:**
```json
{
  "query": "Sony WH-1000XM5",
  "store": "amazon",
  "country": "IN",
  "max_items": 5,
  "save_to_db": true
}
```

**Response:**
```json
{
  "query": "Sony WH-1000XM5",
  "is_url": false,
  "target_store": "amazon",
  "quotes": [
    {
      "title": "Sony WH-1000XM5 Wireless Noise Cancelling Headphones - Black",
      "price": 29090.30,
      "currency": "INR",
      "store_name": "Amazon India",
      "store_code": "amazon",
      "store_badge_emoji": "🛒",
      "store_url": "https://www.amazon.in/...",
      "rating": 4.6,
      "in_stock": true,
      "delivery_info": "Prime Free 1-Day Delivery",
      "is_lowest": true,
      "difference_from_lowest": 0.0
    }
  ],
  "cheapest_store": "Amazon India",
  "lowest_price": 29090.30,
  "highest_price": 30889.70,
  "max_savings": 1799.40,
  "savings_percentage": 5.83,
  "is_live": true,
  "data_source": "Live Apify Actor (junglee/amazon-crawler)",
  "db_records_created": 6,
  "tracked_product_id": 4
}
```

---

## 5. Connecting Apify MCP to Antigravity

Apify provides an official **Model Context Protocol (MCP)** server:
Repository: [https://github.com/apify/apify-mcp-server](https://github.com/apify/apify-mcp-server)

To allow Antigravity or other AI coding agents to search, execute, and inspect Apify scrapers directly:

### Option A: Streamable HTTP (Hosted Remote Server)
Add to `~/.gemini/config/mcp_config.json`:

```json
{
  "mcpServers": {
    "apify": {
      "url": "https://mcp.apify.com/"
    }
  }
}
```

### Option B: Local `stdio` via `npx`
```json
{
  "mcpServers": {
    "apify": {
      "command": "npx",
      "args": ["-y", "@apify/actors-mcp-server"],
      "env": {
        "APIFY_TOKEN": "YOUR_APIFY_API_TOKEN"
      }
    }
  }
}
```

Once connected, your AI assistant can discover actors, run automated web scrapes, and stream real dataset items into your workspace on demand.
