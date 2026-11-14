import os
import sys
from decimal import Decimal

# Ensure backend root is on sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.seed import seed_sample_data
from app.models.product import Product
from app.models.price_observation import PriceObservation
from app.services.apify_scraper import (
    ApifyProductQuote,
    ApifyScraperService,
    apify_service,
    parse_raw_price,
)
from app.api.routes import get_apify_status, run_apify_scrape, ApifyScrapeRequest

TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        seed_sample_data(db)
        yield db
    finally:
        db.close()


def test_parse_raw_price():
    # Numeric
    p, curr = parse_raw_price(19999.50)
    assert p == Decimal("19999.50")
    assert curr == "INR"

    # Dictionary shape
    p, curr = parse_raw_price({"value": 299.99, "currency": "USD"})
    assert p == Decimal("299.99")
    assert curr == "USD"

    # Formatted currency string
    p, curr = parse_raw_price("₹ 24,999.00")
    assert p == Decimal("24999.00")
    assert curr == "INR"

    p, curr = parse_raw_price("$1,299.00")
    assert p == Decimal("1299.00")
    assert curr == "USD"

    # None and empty
    p, curr = parse_raw_price(None)
    assert p is None
    p, curr = parse_raw_price("N/A")
    assert p is None


def test_apify_status_offline():
    status = apify_service.test_connection()
    assert isinstance(status, dict)
    assert "configured" in status
    assert "connected" in status
    assert "message" in status


def test_apify_scrape_simulation(db_session):
    result = apify_service.scrape(
        query_or_url="Sony WH-1000XM5",
        store="amazon",
        country="IN",
        max_items=3,
        save_to_db=True,
        db=db_session,
    )

    assert result.query == "Sony WH-1000XM5"
    assert len(result.quotes) > 0
    assert result.lowest_price is not None
    assert result.lowest_price > 0
    assert result.tracked_product_id is not None
    assert result.db_records_created > 0

    # Verify database persistence
    prod = db_session.get(Product, result.tracked_product_id)
    assert prod is not None
    assert "Sony" in prod.name
    assert len(prod.observations) > 0


def test_apify_api_endpoints(db_session):
    status = get_apify_status()
    assert isinstance(status, dict)

    req = ApifyScrapeRequest(
        query="Apple iPhone 16",
        store="amazon",
        save_to_db=True,
    )
    res = run_apify_scrape(payload=req, db=db_session)
    assert res.lowest_price is not None
    assert res.cheapest_store is not None
    assert res.tracked_product_id is not None


def test_mcp_info_and_tools():
    from app.api.routes import get_mcp_info
    from app.mcp.server import create_mcp_server

    info = get_mcp_info()
    assert isinstance(info, dict)
    assert info["server_name"] == "ecominsights-crawler-mcp"
    assert len(info["tools"]) >= 4

    server = create_mcp_server()
    assert server is not None
    assert server.name == "ecominsights-crawler-mcp"

