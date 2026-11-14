"""Model Context Protocol (MCP) Server for EcomInsights Apify Crawlers.

Exposes Amazon India and Flipkart crawlers as standardized MCP tools
compatible with Claude Desktop, Cursor, Antigravity, and any MCP client.
"""

import json
import logging
import os
import sys
from decimal import Decimal
from typing import Any, Dict, List, Optional

logger = logging.getLogger("ecominsights.mcp")


def _json_serial(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Type {type(obj)} not serializable")


def create_mcp_server():
    """Create and configure the official MCPServer instance."""
    try:
        from mcp.server.mcpserver import MCPServer
    except ImportError:
        logger.warning("mcp package not installed; run: pip install mcp")
        return None

    server = MCPServer("ecominsights-crawler-mcp")
    _register_tools_on_mcpserver(server)
    return server


def _register_tools_on_mcpserver(server):
    from app.services.apify_scraper import apify_service
    from app.services.safe_url_resolver import is_shortened_retailer_url, resolve_short_url_safely
    from app.core.config import settings

    @server.tool()
    def get_crawler_status() -> str:
        """Check Apify crawler API connectivity, account tier, and configured actor slugs.

        Returns status JSON with connected status, username, plan, and active actors.
        """
        status = apify_service.test_connection()
        status["configured_actors"] = {
            "amazon": settings.apify_amazon_actor,
            "flipkart": settings.apify_flipkart_actor,
        }
        return json.dumps(status, indent=2)

    @server.tool()
    def resolve_shortlink(url: str) -> str:
        """Dereference shortened retailer mobile links (amzn.in/d/..., dl.flipkart.com/...)
        into canonical full product URLs with ASIN or Product ID.
        """
        canonical, domain, is_short = resolve_short_url_safely(url)
        return json.dumps({
            "original_url": url,
            "resolved_url": canonical,
            "domain": domain,
            "was_shortened": is_short,
        }, indent=2)

    @server.tool()
    def scrape_amazon(query_or_url: str, country: str = "IN", max_items: int = 5) -> str:
        """Scrape live Amazon India listings for a keyword or product link using the Apify Amazon Crawler.

        Args:
            query_or_url: Amazon product URL (or shortened amzn.in link) or search keyword (e.g. 'boAt Rockerz 480').
            country: 2-letter country code (default 'IN').
            max_items: Maximum product listings to extract (default 5).
        """
        res = apify_service.scrape(
            query_or_url=query_or_url,
            store="amazon",
            country=country,
            max_items=max_items,
            save_to_db=False,
        )
        return json.dumps({
            "query": res.query,
            "target_store": "Amazon India",
            "lowest_price": float(res.lowest_price) if res.lowest_price else None,
            "currency": res.quotes[0].currency if res.quotes else "INR",
            "data_source": res.data_source,
            "is_live": res.is_live,
            "listings_count": len(res.quotes),
            "listings": [
                {
                    "title": q.title,
                    "price": float(q.price),
                    "currency": q.currency,
                    "store": q.store_name,
                    "rating": q.rating,
                    "reviews_count": q.reviews_count,
                    "in_stock": q.in_stock,
                    "delivery": q.delivery_info,
                    "url": q.store_url,
                    "asin": q.asin,
                }
                for q in res.quotes
            ],
            "recommendation": res.recommendation_summary,
        }, indent=2, default=_json_serial)

    @server.tool()
    def scrape_flipkart(query_or_url: str, max_items: int = 5) -> str:
        """Scrape live Flipkart product listings for a keyword or product link using the Apify Flipkart Crawler.

        Args:
            query_or_url: Flipkart product URL or search keyword (e.g. 'boAt Rockerz 480').
            max_items: Maximum product listings to extract (default 5).
        """
        res = apify_service.scrape(
            query_or_url=query_or_url,
            store="flipkart",
            country="IN",
            max_items=max_items,
            save_to_db=False,
        )
        return json.dumps({
            "query": res.query,
            "target_store": "Flipkart",
            "lowest_price": float(res.lowest_price) if res.lowest_price else None,
            "currency": res.quotes[0].currency if res.quotes else "INR",
            "data_source": res.data_source,
            "is_live": res.is_live,
            "listings_count": len(res.quotes),
            "listings": [
                {
                    "title": q.title,
                    "price": float(q.price),
                    "currency": q.currency,
                    "store": q.store_name,
                    "rating": q.rating,
                    "reviews_count": q.reviews_count,
                    "in_stock": q.in_stock,
                    "delivery": q.delivery_info,
                    "url": q.store_url,
                    "product_id": q.asin,
                }
                for q in res.quotes
            ],
            "recommendation": res.recommendation_summary,
        }, indent=2, default=_json_serial)

    @server.tool()
    def compare_amazon_and_flipkart(query_or_url: str, country: str = "IN", max_items: int = 6) -> str:
        """Crawl BOTH Amazon India and Flipkart simultaneously and perform cross-store arbitrage comparison.

        Identifies which store has the lowest price, calculates potential savings,
        and provides direct purchase links to both retailers.

        Args:
            query_or_url: Product search query or link from either Amazon or Flipkart.
            country: 2-letter country code (default 'IN').
            max_items: Cap on total listings combined (default 6).
        """
        res = apify_service.scrape(
            query_or_url=query_or_url,
            store="both",
            country=country,
            max_items=max_items,
            save_to_db=False,
        )
        return json.dumps({
            "query": res.query,
            "stores_compared": ["Amazon India", "Flipkart"],
            "cheapest_store": res.cheapest_store,
            "lowest_price": float(res.lowest_price) if res.lowest_price else None,
            "highest_price": float(res.highest_price) if res.highest_price else None,
            "max_savings": float(res.max_savings) if res.max_savings else None,
            "savings_percentage": res.savings_percentage,
            "arbitrage_summary": res.recommendation_summary,
            "is_live": res.is_live,
            "data_source": res.data_source,
            "quotes": [
                {
                    "store": q.store_name,
                    "store_code": q.store_code,
                    "title": q.title,
                    "price": float(q.price),
                    "currency": q.currency,
                    "is_lowest": q.is_lowest,
                    "difference_from_lowest": float(q.difference_from_lowest or 0),
                    "rating": q.rating,
                    "reviews_count": q.reviews_count,
                    "delivery": q.delivery_info,
                    "url": q.store_url,
                }
                for q in res.quotes
            ],
        }, indent=2, default=_json_serial)


def run_server(transport: str = "stdio"):
    """Run the MCP server over stdio transport."""
    server = create_mcp_server()
    if server:
        logger.info("Starting EcomInsights MCP Server (stdio)...")
        server.run(transport=transport)
    else:
        # Fallback to zero-dependency JSON-RPC stdio loop
        _run_fallback_jsonrpc_stdio()


def _run_fallback_jsonrpc_stdio():
    """Fallback standard JSON-RPC 2.0 loop if mcp package is missing."""
    from app.services.apify_scraper import apify_service
    from app.services.safe_url_resolver import resolve_short_url_safely

    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break
            req = json.loads(line)
            req_id = req.get("id")
            method = req.get("method")
            params = req.get("params", {})

            if method == "initialize":
                resp = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "serverInfo": {"name": "ecominsights-crawler-mcp", "version": "1.0.0"},
                        "capabilities": {"tools": {}},
                    },
                }
            elif method == "tools/list":
                resp = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "tools": [
                            {
                                "name": "compare_amazon_and_flipkart",
                                "description": "Crawl Amazon and Flipkart simultaneously for head-to-head price arbitrage.",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {"query_or_url": {"type": "string"}},
                                    "required": ["query_or_url"],
                                },
                            },
                            {
                                "name": "scrape_amazon",
                                "description": "Scrape Amazon India product listings via Apify.",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {"query_or_url": {"type": "string"}},
                                    "required": ["query_or_url"],
                                },
                            },
                            {
                                "name": "scrape_flipkart",
                                "description": "Scrape Flipkart product listings via Apify.",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {"query_or_url": {"type": "string"}},
                                    "required": ["query_or_url"],
                                },
                            },
                            {
                                "name": "get_crawler_status",
                                "description": "Check Apify crawler API connectivity and status.",
                                "inputSchema": {"type": "object", "properties": {}},
                            },
                        ]
                    },
                }
            elif method == "tools/call":
                tool_name = params.get("name")
                args = params.get("arguments", {})
                q = args.get("query_or_url", "")
                if tool_name == "compare_amazon_and_flipkart":
                    res = apify_service.scrape(q, store="both", save_to_db=False)
                    text = f"Lowest: {res.cheapest_store} at ₹{res.lowest_price}. {res.recommendation_summary}"
                elif tool_name == "scrape_amazon":
                    res = apify_service.scrape(q, store="amazon", save_to_db=False)
                    text = f"Found {len(res.quotes)} Amazon listings. Lowest: ₹{res.lowest_price}"
                elif tool_name == "scrape_flipkart":
                    res = apify_service.scrape(q, store="flipkart", save_to_db=False)
                    text = f"Found {len(res.quotes)} Flipkart listings. Lowest: ₹{res.lowest_price}"
                elif tool_name == "get_crawler_status":
                    text = json.dumps(apify_service.test_connection())
                else:
                    text = f"Unknown tool {tool_name}"
                resp = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {"content": [{"type": "text", "text": text}]},
                }
            else:
                resp = {"jsonrpc": "2.0", "id": req_id, "result": {}}

            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()
        except Exception as e:
            logger.error("JSON-RPC error: %s", e)


if __name__ == "__main__":
    run_server()
