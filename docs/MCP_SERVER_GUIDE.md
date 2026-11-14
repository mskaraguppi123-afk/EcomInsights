# EcomInsights Apify Crawlers — Model Context Protocol (MCP) Server Guide

## 1. Overview
The **EcomInsights MCP Server** exposes live e-commerce crawling capabilities across **Amazon India** and **Flipkart** as standardized **Model Context Protocol (MCP)** tools. Any MCP-compatible AI client (such as Claude Desktop, Cursor, Antigravity, or custom agent frameworks) can connect to this server to discover, search, and extract live prices, ratings, and cross-store arbitrage data on-demand.

---

## 2. Available MCP Tools

| Tool Name | Parameters | Description |
| :--- | :--- | :--- |
| `compare_amazon_and_flipkart` | `query_or_url` *(string)*, `country` *(string, default "IN")*, `max_items` *(int, default 6)* | Crawls Amazon and Flipkart concurrently, compares prices, calculates price differences and percentage savings, and recommends the best deal. |
| `scrape_amazon` | `query_or_url` *(string)*, `country` *(string, default "IN")*, `max_items` *(int, default 5)* | Extracts live product titles, prices, ratings, review counts, Prime eligibility, and canonical URLs from Amazon India via Apify (`junglee/amazon-crawler`). |
| `scrape_flipkart` | `query_or_url` *(string)*, `max_items` *(int, default 5)* | Extracts live product listings, prices, ratings, review counts, Flipkart Assured badges, and URLs from Flipkart via Apify (`scrapesage/flipkart-scraper`). |
| `resolve_shortlink` | `url` *(string)* | Dereferences mobile shortlinks (`amzn.in/d/...`, `dl.flipkart.com/...`) into full canonical product links with ASIN or Product ID. |
| `get_crawler_status` | *None* | Verifies connectivity to the Apify platform, checks API token validity, and reports account tier and configured crawler slugs. |

---

## 3. How to Run Locally

### Quick Launch (Windows)
Double-click:
```bat
start-mcp.bat
```

### Or via Terminal
```bash
python run_mcp_server.py
```
*The server starts on standard I/O (`stdio`) using JSON-RPC 2.0 messages.*

---

## 4. Connecting to AI Clients

### A. Claude Desktop
Add the following to your `claude_desktop_config.json` (`%APPDATA%\Claude\claude_desktop_config.json` on Windows):

```json
{
  "mcpServers": {
    "ecominsights": {
      "command": "python",
      "args": [
        "C:\\Users\\MANJUNATH\\Documents\\Codex\\2026-10-03\\referenced-chatgpt-conversation-this-is-an\\outputs\\EcomInsights\\run_mcp_server.py"
      ],
      "env": {
        "PYTHONUNBUFFERED": "1"
      }
    }
  }
}
```

### B. Cursor / Custom MCP Client
In your project `mcp.json`:

```json
{
  "mcpServers": {
    "ecominsights-crawlers": {
      "command": "python",
      "args": ["run_mcp_server.py"]
    }
  }
}
```

---

## 5. REST API Integration
The FastAPI backend also exposes the crawler status and MCP tool list via standard HTTP endpoints:
- `GET /api/v1/mcp/info`: Metadata and registered tool specifications.
- `GET /api/v1/apify/status`: Cloud crawler connection test.
- `POST /api/v1/apify/scrape`: Direct HTTP execution of the crawler engine.
