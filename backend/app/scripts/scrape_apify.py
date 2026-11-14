"""CLI Script to test and run Apify e-commerce product scrapers.

Usage:
    # Check Apify configuration and account connectivity
    python -m app.scripts.scrape_apify --status

    # Scrape a product by query or direct URL
    python -m app.scripts.scrape_apify --query "Sony WH-1000XM5"

    # Scrape and save observations directly to the local EcomInsights database
    python -m app.scripts.scrape_apify --query "iPhone 16" --save
"""

import argparse
import os
import sys
from decimal import Decimal

# Ensure backend root is on sys.path
_script_dir = os.path.dirname(os.path.abspath(__file__))
_backend_dir = os.path.abspath(os.path.join(_script_dir, "..", ".."))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from app.db.session import SessionLocal
from app.services.apify_scraper import apify_service


def main():
    parser = argparse.ArgumentParser(description="EcomInsights Apify E-commerce Scraper")
    parser.add_argument(
        "--status",
        action="store_true",
        help="Check Apify API token and account connection status",
    )
    parser.add_argument(
        "--query",
        type=str,
        help="Product name or e-commerce URL to scrape",
    )
    parser.add_argument(
        "--store",
        type=str,
        default="both",
        choices=["both", "amazon", "flipkart", "all"],
        help="Target retailer to crawl: 'both', 'amazon', or 'flipkart' (default: both)",
    )
    parser.add_argument(
        "--country",
        type=str,
        default="IN",
        help="Target country code (default: IN)",
    )
    parser.add_argument(
        "--max-items",
        type=int,
        default=5,
        help="Maximum number of listings to extract (default: 5)",
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help="Persist scraped product and price observation to database",
    )

    args = parser.parse_args()

    if args.status:
        print("\n=== Apify Integration Status ===")
        status = apify_service.test_connection()
        for k, v in status.items():
            print(f"  {k}: {v}")
        print("================================\n")
        return

    if not args.query:
        print("Error: Please provide --query <product_or_url> or check --status.")
        sys.exit(1)

    print(f"\n[Apify Scraper] Scraping '{args.query}' on {args.store.upper()} (Country: {args.country})...")
    print(f"[Apify Scraper] Configured: {'LIVE Apify Cloud' if apify_service.is_configured else 'OFFLINE Simulation Mode'}")

    db = SessionLocal() if args.save else None
    try:
        result = apify_service.scrape(
            query_or_url=args.query,
            store=args.store,
            country=args.country,
            max_items=args.max_items,
            save_to_db=args.save,
            db=db,
        )

        print("\n" + "=" * 65)
        print(f" Data Source: {result.data_source}")
        print(f" Live Crawl:  {result.is_live}")
        print(f" Message:     {result.message}")
        print("=" * 65)

        if not result.quotes:
            print(" No quotes found.")
            return

        print(f"\nFound {len(result.quotes)} listing(s):")
        for i, q in enumerate(result.quotes, 1):
            badge = "★ BEST DEAL" if q.is_lowest else ""
            print(f"\n  [{i}] {q.title}")
            print(f"      Store:    {q.store_name} ({q.store_badge_emoji})")
            print(f"      Price:    {q.currency} {q.price:.2f} {badge}")
            print(f"      Rating:   {q.rating} ★ ({q.reviews_count or 'N/A'} reviews)")
            print(f"      Delivery: {q.delivery_info} | In Stock: {q.in_stock}")
            print(f"      URL:      {q.store_url}")

        print("\n" + "-" * 65)
        print(f" Arbitrage Summary:")
        print(f"   Cheapest Store:  {result.cheapest_store}")
        print(f"   Lowest Price:    {result.quotes[0].currency} {result.lowest_price:.2f}")
        print(f"   Highest Price:   {result.quotes[0].currency} {result.highest_price:.2f}")
        print(f"   Max Savings:     {result.quotes[0].currency} {result.max_savings:.2f} ({result.savings_percentage}%)")
        print(f"   Recommendation:  {result.recommendation_summary}")

        if args.save:
            print(f"\n Database Sync:")
            print(f"   Tracked Product ID:  {result.tracked_product_id}")
            print(f"   Observations Added:  {result.db_records_created}")

        print("-" * 65 + "\n")

    finally:
        if db:
            db.close()


if __name__ == "__main__":
    main()
