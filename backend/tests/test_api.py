import os
import sys

# Ensure backend root is on sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.seed import seed_sample_data
from app.db.session import get_db
from app.core.config import settings
import app.main as app_module

# Ensure tests run predictably offline without external API latency
settings.serpapi_api_key = None

TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
app_module.engine = test_engine
app = app_module.app
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
        yield db
    finally:
        db.close()


@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_health_check(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "EcomInsights" in data["app"]


def test_seed_and_list_products(client, db_session):
    # Initial state: empty products list
    response = client.get("/api/v1/products")
    assert response.status_code == 200
    assert response.json() == []

    # Run seed
    seed_result = seed_sample_data(db_session)
    assert seed_result["products_created"] == 3
    assert seed_result["observations_created"] == 9

    # Verify idempotency (no duplicates created on second run)
    re_seed = seed_sample_data(db_session)
    assert re_seed["products_created"] == 0
    assert re_seed["observations_created"] == 0

    # Retrieve products
    response = client.get("/api/v1/products")
    assert response.status_code == 200
    products = response.json()
    assert len(products) == 3

    names = [p["name"] for p in products]
    assert "Wireless Mouse" in names
    assert "Steel Water Bottle" in names
    assert "Sony Headphones" in names

    mouse = next(p for p in products if p["name"] == "Wireless Mouse")
    assert mouse["category"] == "Accessories"
    assert mouse["currency"] == "INR"
    assert mouse["latest_price"] == "779.00"

    # Retrieve single product details with observation history
    detail_res = client.get(f"/api/v1/products/{mouse['id']}")
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["name"] == "Wireless Mouse"
    assert len(detail["observations"]) == 3
    assert detail["observations"][0]["price"] == "799.00"
    assert detail["observations"][1]["price"] == "749.00"
    assert detail["observations"][2]["price"] == "779.00"
    assert detail["insight"] is not None
    assert detail["insight"]["observation_count"] == 3
    assert detail["insight"]["lowest_price"] == "749.00"
    assert detail["insight"]["highest_price"] == "799.00"


def test_product_not_found(client):
    response = client.get("/api/v1/products/99999")
    assert response.status_code == 404


def test_product_insight_endpoint(client):
    response = client.get("/api/v1/products/1/insight")
    assert response.status_code == 200
    insight = response.json()
    assert "predicted_next_price" in insight
    assert insight["trend_direction"] in ["UP", "DOWN", "STABLE"]
    assert insight["recommendation"] in ["BUY_NOW", "WAIT", "NEUTRAL"]
    assert insight["lowest_price"] == "749.00"
    assert insight["highest_price"] == "799.00"


def test_post_seed_endpoint(client):
    response = client.post("/api/v1/seed")
    assert response.status_code == 200
    data = response.json()
    assert "products_created" in data
    assert "observations_created" in data
    assert "Database seeding completed successfully." in data["message"]


def test_web_dashboard(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "EcomInsights" in response.text
    assert "Price Intelligence Dashboard" in response.text


def test_add_price_observation(client):
    # Add a price spike of 999.00 to product 1
    post_res = client.post(
        "/api/v1/products/1/observations",
        json={"price": "999.00", "source_label": "live_check"},
    )
    assert post_res.status_code == 201
    updated = post_res.json()
    assert len(updated["observations"]) == 4
    assert updated["latest_price"] == "999.00"
    assert updated["insight"]["recommendation"] == "WAIT"
    assert updated["insight"]["highest_price"] == "999.00"


def test_compare_target_price(client):
    # Test checking an all-time low deal (e.g. 500 on product 1)
    res_low = client.get("/api/v1/products/1/compare?price=500.00")
    assert res_low.status_code == 200
    data_low = res_low.json()
    assert data_low["deal_rating"] == "ALL_TIME_LOW"
    assert data_low["simulated_recommendation"] == "BUY_NOW"
    assert "cheaper than the lowest recorded price" in data_low["deal_summary"]

    # Verify that the comparison did NOT alter product 1's observations!
    prod_res = client.get("/api/v1/products/1")
    assert prod_res.status_code == 200
    prod = prod_res.json()
    # Still 4 observations, not 5
    assert len(prod["observations"]) == 4

    # Test checking an overpriced deal (e.g. 1500 on product 1)
    res_high = client.get("/api/v1/products/1/compare?price=1500.00")
    assert res_high.status_code == 200
    data_high = res_high.json()
    assert data_high["deal_rating"] == "ALL_TIME_HIGH"
    assert data_high["simulated_recommendation"] == "WAIT"


def test_reset_database(client):
    # Call reset endpoint
    res = client.post("/api/v1/reset")
    assert res.status_code == 200
    data = res.json()
    assert "Database reset to pristine sample data successfully." in data["message"]
    assert data["products_created"] == 3
    assert data["observations_created"] == 9

    # Product 1 should now be back to clean 3 observations, not 4
    prod_res = client.get("/api/v1/products/1")
    assert prod_res.status_code == 200
    assert len(prod_res.json()["observations"]) == 3


def test_multi_store_comparison(client):
    res = client.get("/api/v1/products/1/multi-store-compare")
    assert res.status_code == 200
    data = res.json()
    assert data["product_id"] == 1
    assert "cheapest_store" in data
    assert len(data["stores"]) >= 1
    assert float(data["max_savings"]) >= 0
    assert "data_source" in data
    assert data["data_source"] in ["Live Google Shopping API", "Local Multi-Store Adapter Simulation"]


def test_universal_search_url(client):
    amazon_url = "https://www.amazon.in/Sony-WH-1000XM4-Cancelling-Headphones-Bluetooth/dp/B0863TXGM3"
    res = client.get(f"/api/v1/search/universal?query={amazon_url}")
    assert res.status_code == 200
    data = res.json()
    assert data["is_url"] is True
    assert "Sony" in data["extracted_title"]
    assert data["source_platform"] == "Amazon India"
    assert len(data["stores"]) >= 1
    assert float(data["lowest_price"]) > 0
    assert data["db_updated"] is True
    assert data["tracked_product_id"] is not None
    assert data["db_action"] in ["created", "updated"]


def test_universal_search_keyword(client):
    res = client.get("/api/v1/search/universal?query=Logitech%20Mouse")
    assert res.status_code == 200
    data = res.json()
    assert data["is_url"] is False
    assert "Logitech" in data["extracted_title"]
    assert len(data["stores"]) >= 1
    assert data["db_updated"] is True
    assert data["tracked_product_id"] is not None
    assert data["db_action"] in ["created", "updated"]


def test_quick_add_product(client):
    res = client.post(
        "/api/v1/products/quick-add",
        json={"name": "Logitech MX Master 3S", "price": "7999.00", "category": "Accessories"},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "Logitech MX Master 3S"
    assert data["latest_price"] == "7999.00"
    assert len(data["observations"]) == 1


def test_model_specific_search_iphone16_vs_iphone18(client):
    """Verify that searching for 'iPhone 16' strictly excludes 'iPhone 18',
    normalizes harmless punctuation/case, ranks exact model matches first,
    and returns an empty list for non-existent models."""
    # Add distinct iPhone models to catalog
    client.post(
        "/api/v1/products/quick-add",
        json={"name": "Apple iPhone 16 (128 GB) - Black", "price": "79900.00", "category": "Smartphones"},
    )
    client.post(
        "/api/v1/products/quick-add",
        json={"name": "Apple iPhone 16 Pro (256 GB) - Desert Titanium", "price": "119900.00", "category": "Smartphones"},
    )
    client.post(
        "/api/v1/products/quick-add",
        json={"name": "Apple iPhone 18 Futuristic Concept (512 GB)", "price": "149900.00", "category": "Smartphones"},
    )

    # 1. Search 'iPhone 16': must return iPhone 16 and 16 Pro, NEVER iPhone 18
    res16 = client.get("/api/v1/products?search=iPhone 16")
    assert res16.status_code == 200
    prods16 = res16.json()
    names16 = [p["name"] for p in prods16]
    assert any("iPhone 16 (128 GB)" in n for n in names16)
    assert any("iPhone 16 Pro" in n for n in names16)
    assert not any("iPhone 18" in n for n in names16), "Query for iPhone 16 must NOT return iPhone 18!"

    # Base model iPhone 16 should rank ahead of iPhone 16 Pro when searching 'iPhone 16'
    assert "iPhone 16 (128 GB)" in prods16[0]["name"]

    # 2. Search 'iPhone 18': must return iPhone 18, NEVER iPhone 16
    res18 = client.get("/api/v1/products?search=iPhone 18")
    assert res18.status_code == 200
    prods18 = res18.json()
    names18 = [p["name"] for p in prods18]
    assert len(names18) == 1
    assert "iPhone 18" in names18[0]
    assert not any("iPhone 16" in n for n in names18), "Query for iPhone 18 must NOT return iPhone 16!"

    # 3. Punctuation, casing, and spacing normalization
    res_hyphen = client.get("/api/v1/products?search=iphone-16")
    assert res_hyphen.status_code == 200
    assert any("iPhone 16 (128 GB)" in p["name"] for p in res_hyphen.json())
    assert not any("iPhone 18" in p["name"] for p in res_hyphen.json())

    res_upper = client.get("/api/v1/products?search=  IPHONE   16  ")
    assert res_upper.status_code == 200
    assert any("iPhone 16 (128 GB)" in p["name"] for p in res_upper.json())
    assert not any("iPhone 18" in p["name"] for p in res_upper.json())

    # 4. Model number non-match: searching iPhone 99 returns empty list (no fallback to other iPhones)
    res99 = client.get("/api/v1/products?search=iPhone 99")
    assert res99.status_code == 200
    assert res99.json() == []


def test_distinct_product_prices_no_generic_fallback(client, db_session):
    """Ensure that distinct products maintain their own unique prices,
    never inherit or copy prices from other items, and return None if no observations exist."""
    from app.models.product import Product

    # Create a product with no observations
    unpriced_prod = Product(
        name="Unpriced Test Gadget",
        category="Electronics",
    )
    db_session.add(unpriced_prod)
    db_session.commit()
    db_session.refresh(unpriced_prod)

    # Check products list
    res = client.get(f"/api/v1/products/{unpriced_prod.id}")
    assert res.status_code == 200
    data = res.json()
    assert data["latest_price"] is None, "Product without observations must have latest_price as None"
    assert data["insight"] is None


def test_universal_search_unverified_product_returns_unavailable(client):
    """Universal search for an unverified/unknown product must NOT fall back to generic
    prices like 69900.00 or 2499.00; it must return has_reliable_match=False and lowest_price=None."""
    res = client.get("/api/v1/search/universal?query=iPhone 18 Ultra Titanium 1TB")
    assert res.status_code == 200
    data = res.json()
    assert data["has_reliable_match"] is False
    assert data["lowest_price"] is None
    assert data["stores"] == []
    assert data["cheapest_store"] in ["Price unavailable", "No comparable prices found"]
    assert ("Price unavailable" in data["recommendation_summary"] or "No comparable prices found" in data["recommendation_summary"])
    # Ensure it didn't pollute the database with fake checkpoints
    assert data["db_updated"] is False


def test_search_matcher_direct_model_conflict():
    """Direct unit tests for search_matcher functions to verify conflict detection and ranking."""
    from app.services.search_matcher import match_product, normalize_search_text, extract_model_identifiers

    # Normalization tests
    assert normalize_search_text("iPhone-16  (128GB)!") == "iphone 16 128gb"
    assert normalize_search_text("Sony WH-1000XM4") == "sony wh 1000xm4"

    # Model conflict: iPhone 16 vs iPhone 18
    matched, score, reason = match_product("iPhone 16", "Apple iPhone 18 256GB")
    assert not matched
    assert score == 0
    assert "Conflicting" in reason

    # Exact match: iPhone 16 vs iPhone 16
    matched, score, reason = match_product("iPhone 16", "iPhone 16")
    assert matched
    assert score == 100

    # Variant distinction: iPhone 16 vs iPhone 16 Pro
    matched, score, _ = match_product("iPhone 16", "Apple iPhone 16 Pro 128GB")
    assert matched
    assert score == 70  # Variant penalty

    # Variant requirement: query wants Pro, candidate is base model
    matched, score, reason = match_product("iPhone 16 Pro", "Apple iPhone 16 128GB")
    assert not matched
    assert score == 0
    assert "Missing requested variant" in reason

    # Alphanumeric codes: WH-1000XM4 vs WH-1000XM5
    matched, score, _ = match_product("Sony WH-1000XM4", "Sony WH-1000XM5 Noise Cancelling Headphones")
    assert not matched
    assert score == 0


def test_parse_serpapi_price_utility():
    """Verify that parse_serpapi_price reads strictly from the item's own response data
    and returns None for missing/unparseable prices."""
    from decimal import Decimal
    from app.services.link_search import parse_serpapi_price

    p1, c1 = parse_serpapi_price({"extracted_price": 79900.0, "price": "₹79,900.00"})
    assert p1 == Decimal("79900.00")
    assert c1 == "INR"

    p2, c2 = parse_serpapi_price({"price": "₹1,19,900.00"})
    assert p2 == Decimal("119900.00")
    assert c2 == "INR"

    p3, c3 = parse_serpapi_price({"extracted_price": 999.0, "price": "$999.00"})
    assert p3 == Decimal("999.00")
    assert c3 == "USD"

    p4, c4 = parse_serpapi_price({"price": "Price on Request"})
    assert p4 is None

    p5, c5 = parse_serpapi_price({})
    assert p5 is None


def test_serpapi_exact_model_matching_rejects_conflicts():
    """Verify that SerpApi results validate every item against requested product model,
    strictly rejecting conflicting model numbers (e.g. iPhone 18 when searching iPhone 16)
    and accessories."""
    from decimal import Decimal
    from unittest.mock import patch, MagicMock
    from app.services.link_search import _query_serpapi_shopping

    mock_items = [
        {
            "position": 1,
            "title": "Apple iPhone 16 (128 GB) - Black",
            "source": "Flipkart",
            "price": "₹79,900.00",
            "extracted_price": 79900.0,
            "link": "https://www.flipkart.com/apple-iphone-16-128gb",
            "rating": 4.7,
            "delivery": "Free Delivery"
        },
        {
            "position": 2,
            "title": "Apple iPhone 18 Futuristic Concept 256GB",
            "source": "Amazon",
            "price": "₹99,900.00",
            "extracted_price": 99900.0,
            "link": "https://www.amazon.in/iphone-18",
            "rating": 4.1
        },
        {
            "position": 3,
            "title": "Spigen Rugged Armor Case for iPhone 16",
            "source": "Amazon",
            "price": "₹1,299.00",
            "extracted_price": 1299.0,
            "link": "https://www.amazon.in/case-iphone-16"
        },
        {
            "position": 4,
            "title": "Apple iPhone 16 (128 GB) - White",
            "source": "Croma",
            "price": "₹78,490.00",
            "extracted_price": 78490.0,
            "link": "https://www.croma.com/iphone-16",
            "rating": 4.8
        },
        {
            "position": 5,
            "title": "Apple iPhone 15 (128 GB)",
            "source": "Reliance Digital",
            "price": "₹59,900.00",
            "extracted_price": 59900.0,
            "link": "https://www.reliancedigital.in/iphone-15",
            "rating": 4.5
        }
    ]

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"shopping_results": mock_items}

    with patch("httpx.Client.get", return_value=mock_response):
        res = _query_serpapi_shopping(
            user_input="iPhone 16",
            extracted_title="iPhone 16",
            is_url=False,
            source_platform="Keyword Query",
            api_key="test_api_key",
            currency="INR",
            trusted_retailers=["amazon", "flipkart", "croma", "reliance"],
        )

        assert res is not None
        assert res.has_reliable_match is True
        assert res.lowest_price == Decimal("78490.00")
        assert "Croma" in res.cheapest_store

        store_titles = [s.matched_product_title for s in res.stores]
        # iPhone 18 MUST be rejected
        assert not any("iPhone 18" in t for t in store_titles), "iPhone 18 must be rejected when searching iPhone 16"
        # iPhone 15 MUST be rejected
        assert not any("iPhone 15" in t for t in store_titles), "iPhone 15 must be rejected when searching iPhone 16"
        # Case accessory MUST be rejected
        assert not any("Case" in t for t in store_titles), "Accessory case must be rejected"


def test_serpapi_each_product_retains_own_price_no_copying():
    """Verify that each store quote reads strictly from its own SerpApi response data,
    never copying prices between products, and handles unparseable prices with None."""
    from decimal import Decimal
    from unittest.mock import patch, MagicMock
    from app.services.link_search import _query_serpapi_shopping

    mock_items = [
        {
            "position": 1,
            "title": "Apple iPhone 16 (128 GB) - Black",
            "source": "Flipkart",
            "price": "₹79,900.00",
            "extracted_price": 79900.0,
            "link": "https://www.flipkart.com/apple-iphone-16-128gb",
            "rating": 4.7
        },
        {
            "position": 2,
            "title": "Apple iPhone 16 (128 GB) - White",
            "source": "Croma",
            "price": "₹78,490.00",
            "extracted_price": 78490.0,
            "link": "https://www.croma.com/iphone-16",
            "rating": 4.8
        },
        {
            "position": 3,
            "title": "Apple iPhone 16 (128 GB) - Pink",
            "source": "Reliance Digital",
            "price": "Price on request",
            "link": "https://www.reliancedigital.in/iphone-16",
            "rating": 4.4
        }
    ]

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"shopping_results": mock_items}

    with patch("httpx.Client.get", return_value=mock_response):
        res = _query_serpapi_shopping(
            user_input="iPhone 16",
            extracted_title="iPhone 16",
            is_url=False,
            source_platform="Keyword Query",
            api_key="test_api_key",
            currency="INR",
            trusted_retailers=["amazon", "flipkart", "croma", "reliance"],
        )

        assert res is not None
        assert len(res.stores) == 3

        croma = next(s for s in res.stores if s.store_code == "croma")
        assert croma.price == Decimal("78490.00")
        assert croma.is_lowest is True
        assert croma.difference_from_lowest == Decimal("0.00")
        assert croma.fetched_at is not None
        assert "croma.com" in croma.store_url

        flipkart = next(s for s in res.stores if s.store_code == "flipkart")
        assert flipkart.price == Decimal("79900.00")
        assert flipkart.is_lowest is False
        assert flipkart.difference_from_lowest == Decimal("1410.00")
        assert flipkart.fetched_at is not None

        # Unparseable price does NOT copy another store's price
        reliance = next(s for s in res.stores if s.store_code == "reliance")
        assert reliance.price is None, "Unparseable price must be None (Price unavailable)"
        assert reliance.difference_from_lowest is None
        assert reliance.is_lowest is False


def test_serpapi_unmatched_model_returns_unavailable():
    """Verify that searching for a non-existent model like iPhone 18 returns price unavailable
    when SerpApi returns conflicting models or only accessories."""
    from unittest.mock import patch, MagicMock
    from app.services.link_search import _query_serpapi_shopping

    mock_items = [
        {
            "position": 1,
            "title": "Apple iPhone 16 (128 GB) - Black",
            "source": "Flipkart",
            "price": "₹79,900.00",
            "extracted_price": 79900.0,
            "link": "https://www.flipkart.com/apple-iphone-16-128gb",
        },
        {
            "position": 2,
            "title": "Spigen Ultra Hybrid Case for iPhone 18",
            "source": "Amazon",
            "price": "₹1,499.00",
            "extracted_price": 1499.0,
            "link": "https://www.amazon.in/case-iphone-18",
        }
    ]

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"shopping_results": mock_items}

    with patch("httpx.Client.get", return_value=mock_response):
        res = _query_serpapi_shopping(
            user_input="iPhone 18",
            extracted_title="iPhone 18",
            is_url=False,
            source_platform="Keyword Query",
            api_key="test_api_key",
            currency="INR"
        )

        assert res is not None
        assert res.has_reliable_match is False
        assert res.lowest_price is None
        assert res.cheapest_store in ["Price unavailable", "No comparable prices found", "No trusted comparable listings found"]
        assert len(res.stores) == 0


def test_serpapi_baba_tools_and_outlier_rejection():
    """Verify that unrelated repair tool vendors (e.g., Baba Tools at ₹1,899) and accessories
    are rejected, and never declared as 'best deal' or lowest price for iPhone 16."""
    from decimal import Decimal
    from unittest.mock import patch, MagicMock
    from app.services.link_search import _query_serpapi_shopping

    mock_items = [
        {
            "position": 1,
            "title": "Sunshine S-918F Plus Edge Screen Separator Baba Tools for iPhone 16",
            "source": "Baba Tools",
            "price": "₹1,899.00",
            "extracted_price": 1899.0,
            "link": "https://www.babatools.com/iphone-16-screen-separator",
        },
        {
            "position": 2,
            "title": "Silicon Protective Bumper Case for iPhone 16",
            "source": "Amazon India",
            "price": "₹699.00",
            "extracted_price": 699.0,
            "link": "https://www.amazon.in/iphone-16-silicon-case",
        },
        {
            "position": 3,
            "title": "Apple iPhone 16 (128 GB) - Ultramarine",
            "source": "Amazon",
            "price": "₹77,900.00",
            "extracted_price": 77900.0,
            "link": "https://www.amazon.in/dp/B0DGH7Z1",
            "rating": 4.7,
        },
        {
            "position": 4,
            "title": "Apple iPhone 16 (128 GB) - Black",
            "source": "Flipkart",
            "price": "₹79,900.00",
            "extracted_price": 79900.0,
            "link": "https://www.flipkart.com/apple-iphone-16-128gb",
            "rating": 4.6,
        },
    ]

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"shopping_results": mock_items}

    with patch("httpx.Client.get", return_value=mock_response):
        res = _query_serpapi_shopping(
            user_input="iPhone 16",
            extracted_title="iPhone 16",
            is_url=False,
            source_platform="Keyword Query",
            api_key="test_api_key",
            currency="INR",
            trusted_retailers=["amazon", "flipkart", "croma"],
        )

        assert res is not None
        assert res.has_reliable_match is True
        # ₹1,899 Baba Tools MUST be rejected
        assert res.lowest_price == Decimal("77900.00")
        assert res.cheapest_store == "Amazon India"
        assert res.max_savings == Decimal("2000.00")  # 79,900 - 77,900

        store_names = [s.store_name for s in res.stores]
        assert "Baba Tools" not in store_names
        assert all("Separator" not in s.matched_product_title for s in res.stores)
        assert all("Case" not in s.matched_product_title for s in res.stores)


def test_serpapi_amazon_flipkart_preference_and_status():
    """Verify Amazon India and Flipkart are prioritized, and missing stores are clearly flagged."""
    from unittest.mock import patch, MagicMock
    from app.services.link_search import _query_serpapi_shopping

    # Mock results contain Amazon India and Croma, but NO Flipkart
    mock_items = [
        {
            "position": 1,
            "title": "Apple iPhone 16 (128 GB) - White",
            "source": "Croma Electronics",
            "price": "₹78,490.00",
            "extracted_price": 78490.0,
            "link": "https://www.croma.com/apple-iphone-16-white",
            "rating": 4.8,
        },
        {
            "position": 2,
            "title": "Apple iPhone 16 (128 GB) - Ultramarine",
            "source": "Amazon India",
            "price": "₹77,900.00",
            "extracted_price": 77900.0,
            "link": "https://www.amazon.in/dp/B0DGH7Z1",
            "rating": 4.7,
        },
    ]

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"shopping_results": mock_items}

    with patch("httpx.Client.get", return_value=mock_response):
        res = _query_serpapi_shopping(
            user_input="iPhone 16",
            extracted_title="iPhone 16",
            is_url=False,
            source_platform="Keyword Query",
            api_key="test_api_key",
            currency="INR",
            trusted_retailers=["amazon", "flipkart", "croma"],
        )

        assert res is not None
        assert res.amazon_found is True
        assert res.flipkart_found is False
        # Amazon India must be ranked first due to priority sorting
        assert res.stores[0].store_name == "Amazon India"
        # Retailer notes must state Flipkart was not found / no results returned
        assert any("Flipkart" in note and ("Not found" in note or "No results returned" in note) for note in res.retailer_status_notes)


def test_serpapi_implausible_price_outlier_rejection():
    """Verify that fraudulent or absurdly low prices (e.g. ₹2,500 for a new iPhone 16)
    are rejected as outliers rather than being treated as lowest price."""
    from decimal import Decimal
    from unittest.mock import patch, MagicMock
    from app.services.link_search import _query_serpapi_shopping

    mock_items = [
        {
            "position": 1,
            "title": "Brand New Apple iPhone 16 (128 GB)",
            "source": "Sketchy Store",
            "price": "₹2,500.00",
            "extracted_price": 2500.0,
            "link": "https://www.sketchystore.com/iphone-16",
        },
        {
            "position": 2,
            "title": "Apple iPhone 16 (128 GB) - Ultramarine",
            "source": "Amazon India",
            "price": "₹77,900.00",
            "extracted_price": 77900.0,
            "link": "https://www.amazon.in/dp/B0DGH7Z1",
            "rating": 4.7,
        },
    ]

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"shopping_results": mock_items}

    with patch("httpx.Client.get", return_value=mock_response):
        res = _query_serpapi_shopping(
            user_input="iPhone 16",
            extracted_title="iPhone 16",
            is_url=False,
            source_platform="Keyword Query",
            api_key="test_api_key",
            currency="INR",
            trusted_retailers=["amazon", "flipkart", "croma"],
        )

        assert res is not None
        # ₹2,500 outlier must NOT be selected as lowest price
        assert res.lowest_price == Decimal("77900.00")
        assert res.cheapest_store == "Amazon India"
        assert not any(s.price == Decimal("2500.00") for s in res.stores)


def test_serpapi_comparable_spec_savings_calculation():
    """Verify that comparisons and savings claims are strictly calculated between
    identical specification tiers (e.g., 128 GB vs 128 GB), avoiding cross-tier distortion."""
    from decimal import Decimal
    from unittest.mock import patch, MagicMock
    from app.services.link_search import _query_serpapi_shopping

    mock_items = [
        {
            "position": 1,
            "title": "Apple iPhone 16 (128 GB) - Ultramarine",
            "source": "Amazon India",
            "price": "₹77,900.00",
            "extracted_price": 77900.0,
            "link": "https://www.amazon.in/dp/B0DGH7Z1",
        },
        {
            "position": 2,
            "title": "Apple iPhone 16 (128 GB) - Black",
            "source": "Flipkart",
            "price": "₹79,900.00",
            "extracted_price": 79900.0,
            "link": "https://www.flipkart.com/apple-iphone-16-128gb",
        },
        {
            "position": 3,
            "title": "Apple iPhone 16 (256 GB) - Teal",
            "source": "Croma Electronics",
            "price": "₹89,900.00",
            "extracted_price": 89900.0,
            "link": "https://www.croma.com/iphone-16-256gb",
        },
    ]

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"shopping_results": mock_items}

    with patch("httpx.Client.get", return_value=mock_response):
        res = _query_serpapi_shopping(
            user_input="iPhone 16",
            extracted_title="iPhone 16",
            is_url=False,
            source_platform="Keyword Query",
            api_key="test_api_key",
            currency="INR",
            trusted_retailers=["amazon", "flipkart", "croma"],
        )

        assert res is not None
        assert res.comparable_spec == "128 GB"
        assert res.is_comparable_comparison is True
        # Lowest price in 128 GB tier is Amazon at 77,900
        assert res.lowest_price == Decimal("77900.00")
        assert res.cheapest_store == "Amazon India"
        # Savings must be between comparable 128 GB models: 79,900 - 77,900 = 2,000
        # (NOT 89,900 - 77,900 = 12,000)
        assert res.max_savings == Decimal("2000.00")

        # 256 GB listing must be marked is_comparable=False
        croma_256 = next(s for s in res.stores if s.store_name == "Croma Electronics")
        assert croma_256.is_comparable is False
        assert croma_256.variant_spec == "256 GB"
        assert croma_256.is_lowest is False
        assert croma_256.difference_from_lowest is None


def test_moto_g96_matching_and_model_conflict():
    """Verify that 'Moto G96' matches common formatting variants such as 'Motorola Moto G 96',
    'Motorola G96', and 'Moto G 96', while strictly rejecting different models like 'Moto G85'."""
    from app.services.search_matcher import match_product

    # Formatting variants of Moto G96 must match
    m1, s1, _ = match_product("Moto G96", "Motorola Moto G 96")
    assert m1 is True, "Moto G96 must match Motorola Moto G 96"
    assert s1 >= 90

    m2, s2, _ = match_product("Moto G96", "Motorola G96")
    assert m2 is True, "Moto G96 must match Motorola G96"
    assert s2 >= 90

    m3, s3, _ = match_product("Moto G96", "Moto G 96")
    assert m3 is True, "Moto G96 must match Moto G 96"
    assert s3 >= 90

    m4, s4, _ = match_product("Moto G96", "Motorola Moto G96 5G (128 GB)")
    assert m4 is True, "Moto G96 must match Motorola Moto G96 5G"
    assert s4 >= 70

    # Conflicting models must be rejected
    m_diff1, s_diff1, _ = match_product("Moto G96", "Moto G85")
    assert m_diff1 is False, "Moto G96 must not match Moto G85"
    assert s_diff1 == 0

    m_diff2, s_diff2, _ = match_product("Moto G96", "Motorola Moto G 85")
    assert m_diff2 is False, "Moto G96 must not match Motorola Moto G 85"
    assert s_diff2 == 0

    m_diff3, s_diff3, _ = match_product("Moto G96", "Moto G54 5G")
    assert m_diff3 is False, "Moto G96 must not match Moto G54"
    assert s_diff3 == 0


def test_serpapi_moto_g96_matches_formatting_variants_rejects_g85_and_accessories():
    """Verify SerpApi results for 'Moto G96' check the full result set, accept valid formatting
    variants like 'Motorola Moto G 96', reject 'Moto G85' and accessories, and accurately report availability."""
    from decimal import Decimal
    from unittest.mock import patch, MagicMock
    from app.services.link_search import _query_serpapi_shopping

    mock_items = [
        {
            "position": 1,
            "title": "Spigen Rugged Armor Case for Motorola Moto G 96",
            "source": "Amazon India",
            "price": "₹999.00",
            "extracted_price": 999.0,
            "link": "https://www.amazon.in/case-moto-g96",
        },
        {
            "position": 2,
            "title": "Motorola Moto G 96 5G (Midnight Blue, 128 GB)",
            "source": "Flipkart",
            "price": "₹17,999.00",
            "extracted_price": 17999.0,
            "link": "https://www.flipkart.com/motorola-moto-g-96-128gb",
            "delivery": "Free delivery by Tomorrow",
            "in_stock": True,
        },
        {
            "position": 3,
            "title": "Motorola G96 (128 GB)",
            "source": "Amazon India",
            "price": "₹17,499.00",
            "extracted_price": 17499.0,
            "link": "https://www.amazon.in/motorola-g96-128gb",
            "delivery": "Prime 1-day delivery",
            "in_stock": True,
        },
        {
            "position": 4,
            "title": "Moto G85 5G (Olive Green, 128 GB)",
            "source": "Croma Electronics",
            "price": "₹16,999.00",
            "extracted_price": 16999.0,
            "link": "https://www.croma.com/moto-g85",
            "in_stock": True,
        },
        {
            "position": 5,
            "title": "Motorola Moto G 96 Back Cover Silicon",
            "source": "Flipkart",
            "price": "₹299.00",
            "extracted_price": 299.0,
            "link": "https://www.flipkart.com/cover-moto-g96",
        },
        {
            "position": 6,
            "title": "Motorola Moto G96 (128 GB) - Starlight",
            "source": "Reliance Digital",
            "price": "₹18,499.00",
            "extracted_price": 18499.0,
            "link": "https://www.reliancedigital.in/moto-g96",
            "delivery": "Currently unavailable",
            "in_stock": False,
        },
    ]

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"shopping_results": mock_items}

    with patch("httpx.Client.get", return_value=mock_response):
        res = _query_serpapi_shopping(
            user_input="Moto G96",
            extracted_title="Moto G96",
            is_url=False,
            source_platform="Keyword Query",
            api_key="test_api_key",
            currency="INR",
        )

        assert res is not None
        assert res.has_reliable_match is True
        # Both Amazon and Flipkart must be found via formatting variants
        assert res.amazon_found is True
        assert res.flipkart_found is True

        store_titles = [s.matched_product_title for s in res.stores]
        # Conflicting model G85 must be rejected
        assert not any("G85" in t for t in store_titles), "Moto G85 must be excluded from Moto G96 results"
        # Accessories must be rejected
        assert not any("Case" in t for t in store_titles), "Spigen case must be excluded"
        assert not any("Cover" in t for t in store_titles), "Back cover must be excluded"

        # Lowest price among in-stock is Amazon India at 17,499
        assert res.lowest_price == Decimal("17499.00")
        assert res.cheapest_store == "Amazon India"

        # Out-of-stock listing on Reliance Digital must NOT be marked in-stock
        reliance = next((s for s in res.stores if s.store_code == "reliance"), None)
        if reliance:
            assert reliance.in_stock is False
            assert "unavailable" in reliance.delivery_info.lower()


def test_serpapi_iphone15_nakedcase_399_rejected_and_excluded_from_savings():
    """Verify that an accessory listing like nakedcase.in at ₹399 or AppleCare+ is rejected/excluded,
    never treated as the phone's lowest price, and never used to calculate a bogus 99.41% savings."""
    from decimal import Decimal
    from unittest.mock import patch, MagicMock
    from app.services.link_search import _query_serpapi_shopping

    mock_items = [
        {
            "position": 1,
            "title": "Ultra Thin Matte Frosted Case For iPhone 15",
            "source": "nakedcase.in",
            "price": "₹399.00",
            "extracted_price": 399.0,
            "link": "https://nakedcase.in/products/iphone-15-ultra-thin-case",
            "in_stock": True,
        },
        {
            "position": 2,
            "title": "AppleCare+ for iPhone 15 (2 Year Protection)",
            "source": "Apple India",
            "price": "₹7,900.00",
            "extracted_price": 7900.0,
            "link": "https://www.apple.com/in/applecare-iphone15",
            "in_stock": True,
        },
        {
            "position": 3,
            "title": "Apple iPhone 15 (128 GB) - Black",
            "source": "Amazon India",
            "price": "₹64,900.00",
            "extracted_price": 64900.0,
            "link": "https://www.amazon.in/dp/B0CHX1W1XY",
            "delivery": "Free delivery by Tomorrow",
            "in_stock": True,
        },
        {
            "position": 4,
            "title": "Apple iPhone 15 (Blue, 128 GB)",
            "source": "Flipkart",
            "price": "₹65,999.00",
            "extracted_price": 65999.0,
            "link": "https://www.flipkart.com/apple-iphone-15-blue-128-gb",
            "delivery": "Free delivery",
            "in_stock": True,
        },
    ]

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"shopping_results": mock_items}

    with patch("httpx.Client.get", return_value=mock_response):
        res = _query_serpapi_shopping(
            user_input="iPhone 15",
            extracted_title="iPhone 15",
            is_url=False,
            source_platform="Keyword Query",
            api_key="test_api_key",
            currency="INR",
        )

        assert res is not None
        assert res.has_reliable_match is True
        assert res.comparable_spec == "128 GB"
        assert res.comparable_condition == "Brand New"
        assert res.is_comparable_comparison is True

        # Lowest price must be Amazon at ₹64,900.00, NEVER ₹399
        assert res.lowest_price == Decimal("64900.00")
        assert res.cheapest_store == "Amazon India"

        # Savings must be between comparable 128 GB Brand New phones: 65,999 - 64,900 = 1,099.00
        # (NOT ₹65,600 / 99.41% fake savings!)
        assert res.max_savings == Decimal("1099.00")
        assert res.savings_percentage < Decimal("10.0")

        # Ensure nakedcase is NOT the lowest price or best deal
        store_names = [s.store_name for s in res.stores]
        assert "nakedcase.in" not in store_names or all(
            s.price_status == "excluded" and not s.is_lowest for s in res.stores if s.store_name == "nakedcase.in"
        )

        amazon_quote = next(s for s in res.stores if s.store_code == "amazon")
        assert amazon_quote.is_lowest is True
        assert amazon_quote.price == Decimal("64900.00")
        assert amazon_quote.condition == "Brand New"
        assert amazon_quote.price_status == "verified"

        flipkart_quote = next(s for s in res.stores if s.store_code == "flipkart")
        assert flipkart_quote.is_lowest is False
        assert flipkart_quote.difference_from_lowest == Decimal("1099.00")


def test_serpapi_condition_separation_new_vs_refurbished():
    """Verify that refurbished and brand new listings are strictly separated and never compared
    against each other to claim misleading savings."""
    from decimal import Decimal
    from unittest.mock import patch, MagicMock
    from app.services.link_search import _query_serpapi_shopping

    mock_items = [
        {
            "position": 1,
            "title": "Apple iPhone 15 (128 GB) - Black",
            "source": "Amazon India",
            "price": "₹64,900.00",
            "extracted_price": 64900.0,
            "link": "https://www.amazon.in/dp/B0CHX1W1XY",
            "in_stock": True,
        },
        {
            "position": 2,
            "title": "Apple iPhone 15 (128 GB) Refurbished - Grade A Superb",
            "source": "Cashify",
            "price": "₹48,000.00",
            "extracted_price": 48000.0,
            "link": "https://www.cashify.in/refurbished-iphone-15",
            "condition": "refurbished",
            "in_stock": True,
        },
    ]

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"shopping_results": mock_items}

    with patch("httpx.Client.get", return_value=mock_response):
        res = _query_serpapi_shopping(
            user_input="iPhone 15",
            extracted_title="iPhone 15",
            is_url=False,
            source_platform="Keyword Query",
            api_key="test_api_key",
            currency="INR",
        )

        assert res is not None
        # Target condition for brand-new query is Brand New
        assert res.comparable_condition == "Brand New"

        # The brand new phone must NOT declare savings against the refurbished quote
        # Since only 1 Brand New quote exists, savings cannot be calculated across conditions
        assert res.max_savings is None
        assert res.is_comparable_comparison is False

        amazon_quote = next(s for s in res.stores if s.store_code == "amazon")
        assert amazon_quote.is_lowest is False  # Single quote does not get lowest/best deal badge


def test_serpapi_single_listing_no_best_deal_claim():
    """Verify that when only 1 valid listing exists, the app does not declare a 'Best deal'
    or compute savings, requiring at least two comparable listings."""
    from decimal import Decimal
    from unittest.mock import patch, MagicMock
    from app.services.link_search import _query_serpapi_shopping

    mock_items = [
        {
            "position": 1,
            "title": "Apple iPhone 15 (128 GB) - Blue",
            "source": "Amazon India",
            "price": "₹64,900.00",
            "extracted_price": 64900.0,
            "link": "https://www.amazon.in/dp/B0CHX1W1XY",
            "in_stock": True,
        },
    ]

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"shopping_results": mock_items}

    with patch("httpx.Client.get", return_value=mock_response):
        res = _query_serpapi_shopping(
            user_input="iPhone 15",
            extracted_title="iPhone 15",
            is_url=False,
            source_platform="Keyword Query",
            api_key="test_api_key",
            currency="INR",
        )

        assert res is not None
        assert res.has_reliable_match is True
        assert res.lowest_price == Decimal("64900.00")
        assert res.cheapest_store == "Amazon India"
        # No savings and no comparable comparison with only 1 listing
        assert res.max_savings is None
        assert res.is_comparable_comparison is False

        # Store quote must NOT be marked is_lowest
        amazon_quote = res.stores[0]
        assert amazon_quote.is_lowest is False
        assert "at least two comparable listings" in res.recommendation_summary.lower()


def test_serpapi_no_comparable_prices_found_state():
    """Verify that if all candidate results are excluded (accessories, repair parts, outliers),
    the app cleanly reports 'No comparable prices found' rather than claiming a false lowest price."""
    from unittest.mock import patch, MagicMock
    from app.services.link_search import _query_serpapi_shopping

    mock_items = [
        {
            "position": 1,
            "title": "Ultra Thin Matte Frosted Case For iPhone 15",
            "source": "nakedcase.in",
            "price": "₹399.00",
            "extracted_price": 399.0,
            "link": "https://nakedcase.in/products/iphone-15-ultra-thin-case",
        },
        {
            "position": 2,
            "title": "iPhone 15 Display Replacement Screen",
            "source": "Baba Tools",
            "price": "₹1,899.00",
            "extracted_price": 1899.0,
            "link": "https://www.babatools.com/iphone-15-display",
        },
        {
            "position": 3,
            "title": "Tempered Glass Screen Protector for iPhone 15",
            "source": "CaseWale",
            "price": "₹199.00",
            "extracted_price": 199.0,
            "link": "https://casewale.com/iphone-15-tempered-glass",
        },
    ]

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"shopping_results": mock_items}

    with patch("httpx.Client.get", return_value=mock_response):
        res = _query_serpapi_shopping(
            user_input="iPhone 15",
            extracted_title="iPhone 15",
            is_url=False,
            source_platform="Keyword Query",
            api_key="test_api_key",
            currency="INR",
        )

        assert res is not None
        assert res.has_reliable_match is False
        assert res.lowest_price is None
        assert res.max_savings is None
        assert res.cheapest_store in ["No comparable prices found", "No trusted comparable listings found"]
        assert not res.is_comparable_comparison


def test_category_and_general_price_plausibility():
    """Verify universal category plausibility floors and median outlier rejection across multiple products."""
    from decimal import Decimal
    from app.services.link_search import is_price_plausible

    # iPhone 15 (premium smartphone floor >= 20,000, known base 64,900)
    p1, _ = is_price_plausible(Decimal("399.00"), "iPhone 15", Decimal("64900.00"), [Decimal("399.00"), Decimal("64900.00")])
    assert p1 is False, "₹399 for iPhone 15 must be rejected"

    p2, _ = is_price_plausible(Decimal("1899.00"), "iPhone 15", Decimal("64900.00"), [Decimal("1899.00"), Decimal("64900.00")])
    assert p2 is False, "₹1,899 for iPhone 15 must be rejected"

    p3, _ = is_price_plausible(Decimal("64900.00"), "iPhone 15", Decimal("64900.00"), [Decimal("64900.00"), Decimal("65999.00")])
    assert p3 is True, "₹64,900 for iPhone 15 is plausible"

    # Moto G96 (smartphone floor >= 4,500)
    p4, _ = is_price_plausible(Decimal("299.00"), "Moto G96", None, [])
    assert p4 is False, "₹299 for Moto G96 must be rejected"

    p5, _ = is_price_plausible(Decimal("17499.00"), "Moto G96", None, [])
    assert p5 is True, "₹17,499 for Moto G96 is plausible"

    # Laptops (laptop floor >= 15,000)
    p6, _ = is_price_plausible(Decimal("2500.00"), "MacBook Pro M3", None, [])
    assert p6 is False, "₹2,500 for MacBook Pro must be rejected"

    p7, _ = is_price_plausible(Decimal("129900.00"), "MacBook Pro M3", None, [])
    assert p7 is True, "₹1,29,900 for MacBook Pro is plausible"

    # Premium Audio (floor >= 6,000)
    p8, _ = is_price_plausible(Decimal("499.00"), "Sony WH-1000XM5", None, [])
    assert p8 is False, "₹499 for Sony WH-1000XM5 must be rejected"

    p9, _ = is_price_plausible(Decimal("26990.00"), "Sony WH-1000XM5", None, [])
    assert p9 is True, "₹26,990 for Sony WH-1000XM5 is plausible"


def test_allowlist_domain_verification_rejects_lookalikes_and_unverified():
    """Verify that verify_retailer_from_url identifies retailers strictly from authentic domains,
    rejecting lookalikes, phishing domains, unverified shops, and non-allowlisted retailers."""
    from app.core.retailer_allowlist import (
        verify_retailer_from_url,
        is_allowed_domain_match,
        get_active_trusted_retailers,
    )

    # 1. Authentic domain matching
    assert is_allowed_domain_match("amazon.in", "amazon.in") is True
    assert is_allowed_domain_match("www.amazon.in", "amazon.in") is True
    assert is_allowed_domain_match("m.amazon.in", "amazon.in") is True
    assert is_allowed_domain_match("flipkart.com", "flipkart.com") is True
    assert is_allowed_domain_match("www.flipkart.com", "flipkart.com") is True
    assert is_allowed_domain_match("dl.flipkart.com", "flipkart.com") is True

    # 2. Deceptive lookalike domains must be rejected
    assert is_allowed_domain_match("amaz0n.in", "amazon.in") is False, "amaz0n.in typo lookalike must be rejected"
    assert is_allowed_domain_match("amazon-deals.in", "amazon.in") is False, "amazon-deals.in prefix must be rejected"
    assert is_allowed_domain_match("fake-amazon.in", "amazon.in") is False, "fake-amazon.in must be rejected"
    assert is_allowed_domain_match("amazon.in.phishing.com", "amazon.in") is False, "Deceptive subdomain on external host must be rejected"
    assert is_allowed_domain_match("flipkart.deals", "flipkart.com") is False, "flipkart.deals TLD must be rejected"
    assert is_allowed_domain_match("flipkart-store.com", "flipkart.com") is False, "flipkart-store.com lookalike must be rejected"
    assert is_allowed_domain_match("nakedcase.in", "amazon.in") is False
    assert is_allowed_domain_match("babatools.com", "flipkart.com") is False

    # 3. Default India allowlist (only Amazon India and Flipkart active)
    active = get_active_trusted_retailers(["amazon", "flipkart"])

    # Authentic Amazon URL
    r_amz = verify_retailer_from_url("https://www.amazon.in/dp/B0CHX1W1XY", active_retailers=active)
    assert r_amz is not None
    assert r_amz.store_code == "amazon"
    assert r_amz.canonical_name == "Amazon India"

    # Authentic Flipkart URL
    r_fk = verify_retailer_from_url("https://www.flipkart.com/apple-iphone-15/p/itm123", active_retailers=active)
    assert r_fk is not None
    assert r_fk.store_code == "flipkart"
    assert r_fk.canonical_name == "Flipkart"

    # Lookalike Amazon URL
    r_lookalike_amz = verify_retailer_from_url("https://amaz0n.in/dp/B0CHX1W1XY", active_retailers=active)
    assert r_lookalike_amz is None, "Lookalike amaz0n.in must return None"

    # Lookalike Flipkart URL
    r_lookalike_fk = verify_retailer_from_url("https://flipkart-deals.in/apple-iphone-15", active_retailers=active)
    assert r_lookalike_fk is None, "Lookalike flipkart-deals.in must return None"

    # Unverified shop (nakedcase.in)
    r_naked = verify_retailer_from_url("https://nakedcase.in/products/iphone-15-case", active_retailers=active)
    assert r_naked is None, "nakedcase.in must return None"

    # Retailer not on active allowlist (e.g. Croma when allowlist is only amazon, flipkart)
    r_croma_disabled = verify_retailer_from_url("https://www.croma.com/iphone-16", active_retailers=active)
    assert r_croma_disabled is None, "Croma must return None when not on active allowlist"

    # Retailer explicitly added to allowlist
    active_with_croma = get_active_trusted_retailers(["amazon", "flipkart", "croma"])
    r_croma_enabled = verify_retailer_from_url("https://www.croma.com/iphone-16", active_retailers=active_with_croma)
    assert r_croma_enabled is not None, "Croma must be verified when explicitly added to allowlist"
    assert r_croma_enabled.store_code == "croma"


def test_serpapi_rejects_lookalike_domains_even_if_displayed_source_claims_retailer():
    """Verify that SerpApi results reject lookalike domains even when the displayed store name claims
    to be Amazon or Flipkart, verifying strictly from the actual result URL domain."""
    from decimal import Decimal
    from unittest.mock import patch, MagicMock
    from app.services.link_search import _query_serpapi_shopping

    mock_items = [
        {
            "position": 1,
            "title": "Apple iPhone 15 (128 GB) - Black",
            "source": "Amazon India",  # Display name claims Amazon!
            "price": "₹59,999.00",
            "extracted_price": 59999.0,
            "link": "https://amaz0n.in/iphone-15",  # Lookalike domain!
            "in_stock": True,
        },
        {
            "position": 2,
            "title": "Apple iPhone 15 (128 GB) - Blue",
            "source": "Flipkart Deals",  # Display name claims Flipkart!
            "price": "₹58,999.00",
            "extracted_price": 58999.0,
            "link": "https://flipkart-deals.in/apple-iphone-15",  # Lookalike domain!
            "in_stock": True,
        },
        {
            "position": 3,
            "title": "Apple iPhone 15 (128 GB) - Black",
            "source": "Amazon India",
            "price": "₹64,900.00",
            "extracted_price": 64900.0,
            "link": "https://www.amazon.in/dp/B0CHX1W1XY",  # Genuine domain!
            "in_stock": True,
        },
        {
            "position": 4,
            "title": "Apple iPhone 15 (Blue, 128 GB)",
            "source": "Flipkart",
            "price": "₹65,900.00",
            "extracted_price": 65900.0,
            "link": "https://www.flipkart.com/apple-iphone-15-blue-128-gb",  # Genuine domain!
            "in_stock": True,
        },
    ]

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"shopping_results": mock_items}

    with patch("httpx.Client.get", return_value=mock_response):
        res = _query_serpapi_shopping(
            user_input="iPhone 15",
            extracted_title="iPhone 15",
            is_url=False,
            source_platform="Keyword Query",
            api_key="test_api_key",
            currency="INR",
        )

        assert res is not None
        assert res.has_reliable_match is True
        # Only the 2 authentic domain listings must survive
        assert len(res.stores) == 2

        store_urls = [s.store_url for s in res.stores]
        assert not any("amaz0n.in" in u for u in store_urls), "amaz0n.in lookalike must be excluded"
        assert not any("flipkart-deals.in" in u for u in store_urls), "flipkart-deals.in lookalike must be excluded"

        # Lowest price must be Amazon India at 64,900.00 (NOT the lookalike 58,999 or 59,999)
        assert res.lowest_price == Decimal("64900.00")
        assert res.cheapest_store == "Amazon India"
        assert res.max_savings == Decimal("1000.00")


def test_serpapi_missing_or_failing_trusted_retailers_shows_no_trusted_listings():
    """Verify that if Amazon India and Flipkart results are missing or fail product and price checks,
    the app cleanly reports 'No trusted comparable listings found' and NEVER fills the space with untrusted stores."""
    from unittest.mock import patch, MagicMock
    from app.services.link_search import _query_serpapi_shopping

    mock_items = [
        {
            "position": 1,
            "title": "Apple iPhone 15 (128 GB)",
            "source": "TechBazaar",
            "price": "₹62,000.00",
            "extracted_price": 62000.0,
            "link": "https://techbazaar.in/iphone-15",
        },
        {
            "position": 2,
            "title": "Apple iPhone 15 (128 GB)",
            "source": "RandomMobiles",
            "price": "₹61,500.00",
            "extracted_price": 61500.0,
            "link": "https://randommobiles.com/iphone-15",
        },
    ]

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"shopping_results": mock_items}

    with patch("httpx.Client.get", return_value=mock_response):
        res = _query_serpapi_shopping(
            user_input="iPhone 15",
            extracted_title="iPhone 15",
            is_url=False,
            source_platform="Keyword Query",
            api_key="test_api_key",
            currency="INR",
        )

        assert res is not None
        assert res.has_reliable_match is False
        assert res.lowest_price is None
        assert res.max_savings is None
        assert res.stores == [], "Must NEVER fill the space with untrusted stores"
        assert res.cheapest_store in ["No trusted comparable listings found", "No comparable prices found"]
        assert res.amazon_found is False
        assert res.flipkart_found is False
        assert "trusted" in res.recommendation_summary.lower() or "allowlisted" in res.recommendation_summary.lower()


def test_serpapi_custom_allowlist_enables_explicitly_added_retailer():
    """Verify that another retailer (e.g. Croma) is included ONLY when explicitly added to the allowlist."""
    from decimal import Decimal
    from unittest.mock import patch, MagicMock
    from app.services.link_search import _query_serpapi_shopping

    mock_items = [
        {
            "position": 1,
            "title": "Apple iPhone 15 (128 GB) - Black",
            "source": "Amazon India",
            "price": "₹64,900.00",
            "extracted_price": 64900.0,
            "link": "https://www.amazon.in/dp/B0CHX1W1XY",
            "in_stock": True,
        },
        {
            "position": 2,
            "title": "Apple iPhone 15 (128 GB) - Blue",
            "source": "Croma Electronics",
            "price": "₹63,990.00",
            "extracted_price": 63990.0,
            "link": "https://www.croma.com/apple-iphone-15-128gb",
            "in_stock": True,
        },
    ]

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"shopping_results": mock_items}

    # Case A: Default allowlist (only Amazon and Flipkart) -> Croma must be EXCLUDED
    with patch("httpx.Client.get", return_value=mock_response):
        res_default = _query_serpapi_shopping(
            user_input="iPhone 15",
            extracted_title="iPhone 15",
            is_url=False,
            source_platform="Keyword Query",
            api_key="test_api_key",
            currency="INR",
            trusted_retailers=["amazon", "flipkart"],
        )
        assert res_default is not None
        store_names = [s.store_name for s in res_default.stores]
        assert "Croma Electronics" not in store_names, "Croma must be excluded under default allowlist"
        assert len(res_default.stores) == 1
        assert res_default.stores[0].store_name == "Amazon India"

    # Case B: Allowlist explicitly includes Croma -> Croma must be INCLUDED
    with patch("httpx.Client.get", return_value=mock_response):
        res_with_croma = _query_serpapi_shopping(
            user_input="iPhone 15",
            extracted_title="iPhone 15",
            is_url=False,
            source_platform="Keyword Query",
            api_key="test_api_key",
            currency="INR",
            trusted_retailers=["amazon", "flipkart", "croma"],
        )
        assert res_with_croma is not None
        store_names = [s.store_name for s in res_with_croma.stores]
        assert "Croma Electronics" in store_names, "Croma must be included when explicitly allowlisted"
        assert len(res_with_croma.stores) == 2
        # Croma is cheaper at 63,990 vs Amazon at 64,900
        assert res_with_croma.lowest_price == Decimal("63990.00")
        assert res_with_croma.cheapest_store == "Croma Electronics"
        assert res_with_croma.max_savings == Decimal("910.00")


def test_allowlist_configuration_helpers_and_settings():
    """Verify programmatic configuration helpers: enable, disable, add, and reset retailers."""
    from app.core.retailer_allowlist import (
        TrustedRetailer,
        PREDEFINED_RETAILERS,
        enable_trusted_retailer,
        disable_trusted_retailer,
        add_trusted_retailer,
        reset_trusted_retailers,
        get_active_trusted_retailers,
    )

    # Reset
    reset_trusted_retailers()
    default_active = get_active_trusted_retailers()
    assert "amazon" in default_active
    assert "flipkart" in default_active
    assert "croma" in default_active
    assert "reliance" in default_active

    # Disable Croma
    assert disable_trusted_retailer("croma") is True
    assert PREDEFINED_RETAILERS["croma"].enabled is False

    # Re-enable Croma
    assert enable_trusted_retailer("croma") is True
    assert PREDEFINED_RETAILERS["croma"].enabled is True

    # Disable Flipkart
    assert disable_trusted_retailer("flipkart") is True
    assert PREDEFINED_RETAILERS["flipkart"].enabled is False

    # Add custom verified retailer
    custom = TrustedRetailer(
        store_code="customstore",
        canonical_name="Custom Verified Store",
        emoji="🏪",
        allowed_domains=["customstore.in"],
        priority=3,
        enabled=True,
        description="Custom verified electronics store",
    )
    add_trusted_retailer(custom)
    assert "customstore" in PREDEFINED_RETAILERS
    assert PREDEFINED_RETAILERS["customstore"].matches_hostname("www.customstore.in") is True
    assert PREDEFINED_RETAILERS["customstore"].matches_hostname("customstore-fake.in") is False

    # Cleanup reset
    reset_trusted_retailers()
    del PREDEFINED_RETAILERS["customstore"]


def test_serpapi_separate_targeted_retailer_discovery():
    """Verify that when primary search lacks Amazon or Flipkart, separate targeted
    queries are executed to discover retailer listings."""
    from decimal import Decimal
    from unittest.mock import patch, MagicMock
    from app.services.link_search import _query_serpapi_shopping

    # Primary query returns generic sponsored listings without Amazon or Flipkart
    primary_items = [
        {
            "position": 1,
            "title": "Apple iPhone 15 (128 GB) - Blue",
            "source": "Vijay Sales",
            "price": "₹64,900.00",
            "extracted_price": 64900.0,
            "link": "https://www.vijaysales.com/apple-iphone-15",
        }
    ]

    # Targeted Amazon query returns authentic Amazon listing
    amazon_items = [
        {
            "position": 1,
            "title": "Apple iPhone 15 (128 GB) - Black",
            "source": "Amazon.in",
            "price": "₹63,999.00",
            "extracted_price": 63999.0,
            "link": "https://www.amazon.in/dp/B0CHX1W1XY",
            "rating": 4.6,
        }
    ]

    # Targeted Flipkart query returns authentic Flipkart listing
    flipkart_items = [
        {
            "position": 1,
            "title": "Apple iPhone 15 (Blue, 128 GB)",
            "source": "Flipkart",
            "price": "₹64,499.00",
            "extracted_price": 64499.0,
            "link": "https://dl.flipkart.com/dl/apple-iphone-15/p/itm",
            "rating": 4.5,
        }
    ]

    def mock_get(url, params=None, **kwargs):
        resp = MagicMock()
        resp.status_code = 200
        q = (params or {}).get("q", "").lower()
        if "amazon" in q:
            resp.json.return_value = {"shopping_results": amazon_items}
        elif "flipkart" in q:
            resp.json.return_value = {"shopping_results": flipkart_items}
        else:
            resp.json.return_value = {"shopping_results": primary_items}
        return resp

    with patch("httpx.Client.get", side_effect=mock_get):
        res = _query_serpapi_shopping(
            user_input="iPhone 15",
            extracted_title="iPhone 15",
            is_url=False,
            source_platform="Keyword Query",
            api_key="test_api_key",
            currency="INR",
            trusted_retailers=["amazon", "flipkart"],
        )

        assert res is not None
        assert res.amazon_found is True
        assert res.flipkart_found is True
        assert len(res.stores) == 2
        assert res.stores[0].store_name == "Amazon India"
        assert res.stores[1].store_name == "Flipkart"
        assert res.lowest_price == Decimal("63999.00")
        assert res.max_savings == Decimal("500.00")
        assert any("Amazon India: Verified listing included." in note for note in res.retailer_status_notes)
        assert any("Flipkart: Verified listing included." in note for note in res.retailer_status_notes)
        assert "amazon" in res.direct_retailer_links
        assert "flipkart" in res.direct_retailer_links


def test_serpapi_accurate_status_notes_for_accessories_and_outliers():
    """Verify that accurate status reasons are reported for rejected accessories and price outliers."""
    from unittest.mock import patch, MagicMock
    from app.services.link_search import _query_serpapi_shopping

    # Primary items: Amazon returns only phone cases; Flipkart returns an implausible outlier ₹1,899
    primary_items = [
        {
            "position": 1,
            "title": "Amazon Basics Shockproof Case for Apple iPhone 16",
            "source": "Amazon.in",
            "price": "₹399.00",
            "extracted_price": 399.0,
            "link": "https://www.amazon.in/dp/B0DCASE",
        },
        {
            "position": 2,
            "title": "Apple iPhone 16 128GB Complete Phone",
            "source": "Flipkart",
            "price": "₹1,899.00",
            "extracted_price": 1899.0,
            "link": "https://www.flipkart.com/apple-iphone-16",
        },
    ]

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"shopping_results": primary_items}

    with patch("httpx.Client.get", return_value=mock_resp):
        res = _query_serpapi_shopping(
            user_input="iPhone 16",
            extracted_title="iPhone 16",
            is_url=False,
            source_platform="Keyword Query",
            api_key="test_api_key",
            currency="INR",
            trusted_retailers=["amazon", "flipkart"],
        )

        assert res is not None
        assert res.amazon_found is False
        assert res.flipkart_found is False
        # Accurate status reason for Amazon (rejected as accessory)
        assert any("Amazon India" in note and "accessories" in note for note in res.retailer_status_notes)
        # Accurate status reason for Flipkart (rejected as outlier)
        assert any("Flipkart" in note and "outlier" in note for note in res.retailer_status_notes)
        # Direct retailer links must be provided
        assert "amazon" in res.direct_retailer_links
        assert "flipkart" in res.direct_retailer_links
        assert any("direct" in note.lower() or "limited" in note.lower() for note in res.retailer_status_notes)


def test_serpapi_title_matching_apple_iphone_15_matches_iphone_15():
    """Verify that 'Apple iPhone 15' matches 'iPhone 15' across harmless formatting,
    while 'iPhone 14' and accessories are rejected."""
    from app.services.search_matcher import match_product
    from app.services.link_search import is_unrelated_or_parts_item

    # Harmless difference: Brand prefix 'Apple iPhone 15' vs query 'iPhone 15'
    is_m, score, reason = match_product("iPhone 15", "Apple iPhone 15 (128 GB) - Blue")
    assert is_m is True
    assert score >= 70

    # Model number conflict: iPhone 14 must not match iPhone 15
    is_m14, score14, reason14 = match_product("iPhone 15", "Apple iPhone 14 (128 GB) - Midnight")
    assert is_m14 is False
    assert score14 == 0
    assert "Conflicting" in reason14

    # Accessory rejection: Case title rejected
    is_bad, _ = is_unrelated_or_parts_item("Silicone Protective Case for Apple iPhone 15", "Amazon.in", "iPhone 15")
    assert is_bad is True


def test_serpapi_google_shopping_internal_links_versus_lookalike_domains():
    """Verify domain verification accepts Google Shopping indexed listings while strictly
    rejecting external lookalike domains."""
    from app.core.retailer_allowlist import verify_retailer_from_url

    # Google Shopping offer URL with authentic Amazon source
    g_url = "https://www.google.co.in/search?ibp=oshop&q=iPhone+15&prds=catalogid:123"
    ret_amz = verify_retailer_from_url(g_url, source_name="amazon.in")
    assert ret_amz is not None
    assert ret_amz.store_code == "amazon"

    # Google Shopping offer URL with authentic Flipkart source
    ret_fk = verify_retailer_from_url(g_url, source_name="Flipkart")
    assert ret_fk is not None
    assert ret_fk.store_code == "flipkart"

    # External lookalike domain: must be rejected even if source says Amazon.in
    fake_url = "https://amaz0n.in/apple-iphone-15/dp/12345"
    ret_fake = verify_retailer_from_url(fake_url, source_name="Amazon.in")
    assert ret_fake is None

    # External lookalike Flipkart domain
    fake_fk_url = "https://flipkart-deals.in/apple-iphone-15"
    ret_fake_fk = verify_retailer_from_url(fake_fk_url, source_name="Flipkart")
    assert ret_fake_fk is None


def test_universal_search_ai_insight_pipeline(client):
    """Verify that universal search computes and returns explainable ML price intelligence."""
    res = client.get("/api/v1/search/universal?query=iPhone+15")
    assert res.status_code == 200
    data = res.json()
    assert "ai_insight" in data
    ai = data["ai_insight"]
    assert ai is not None
    assert "predicted_next_price" in ai
    assert float(ai["predicted_next_price"]) > 0
    assert ai["trend_direction"] in ["UP", "DOWN", "STABLE"]
    assert ai["recommendation"] in ["BUY_NOW", "WAIT", "NEUTRAL"]
    assert len(ai["recommendation_reason"]) > 5
    assert "algorithm" in ai
    assert "Ensemble EMA" in ai["algorithm"]

    # Verify Croma, Reliance, Vijay Sales etc. are active stores in comparison
    store_codes = [s["store_code"] for s in data["stores"]]
    assert "croma" in store_codes or "croma" in data.get("direct_retailer_links", {})


def test_retailer_product_url_validation_and_lookalike_rejection():
    """Verify that only HTTPS links on verified retailer domains are accepted,
    unpacking Google redirects, and rejecting lookalikes, non-HTTPS, and malformed URLs."""
    from app.core.retailer_allowlist import (
        validate_and_sanitize_retailer_product_url,
        extract_destination_url,
    )

    # 1. Authentic direct HTTPS Amazon India link
    amz_valid = "https://www.amazon.in/Apple-iPhone-15-128-GB/dp/B0CHX1W1XY/"
    assert validate_and_sanitize_retailer_product_url(amz_valid, "amazon") == amz_valid

    # 2. Authentic direct HTTPS Flipkart link
    fk_valid = "https://www.flipkart.com/apple-iphone-15-black-128-gb/p/itm6ac6485515ae4"
    assert validate_and_sanitize_retailer_product_url(fk_valid, "flipkart") == fk_valid

    # 3. Google redirect (/aclk or /url) unpacking to Amazon / Flipkart
    g_aclk = f"https://www.google.com/aclk?sa=l&ai=DChcSEw&adurl={amz_valid}"
    assert validate_and_sanitize_retailer_product_url(g_aclk, "amazon") == amz_valid

    g_url = f"https://www.google.com/url?url={fk_valid}"
    assert validate_and_sanitize_retailer_product_url(g_url, "flipkart") == fk_valid

    # 4. Reject Google search / shopping aggregation pages as product URLs
    g_shop = "https://www.google.co.in/search?ibp=oshop&q=iPhone 15&prds=catalogid:123"
    assert validate_and_sanitize_retailer_product_url(g_shop, "amazon") is None
    assert validate_and_sanitize_retailer_product_url(g_shop, "flipkart") is None

    # 5. Reject non-HTTPS links (http://)
    assert validate_and_sanitize_retailer_product_url("http://www.amazon.in/dp/B0CHX1W1XY", "amazon") is None
    assert validate_and_sanitize_retailer_product_url("http://www.flipkart.com/item", "flipkart") is None

    # 6. Reject lookalike domains
    assert validate_and_sanitize_retailer_product_url("https://amaz0n.in/dp/B0CHX1W1XY", "amazon") is None
    assert validate_and_sanitize_retailer_product_url("https://amazon-deals.in/dp/123", "amazon") is None
    assert validate_and_sanitize_retailer_product_url("https://flipkart-deals.in/item", "flipkart") is None
    assert validate_and_sanitize_retailer_product_url("https://fake-amazon.in/item", "amazon") is None

    # 7. Reject empty, '#', javascript:, or malformed URLs with unencoded spaces
    assert validate_and_sanitize_retailer_product_url("", "amazon") is None
    assert validate_and_sanitize_retailer_product_url("#", "amazon") is None
    assert validate_and_sanitize_retailer_product_url("javascript:void(0)", "amazon") is None
    assert validate_and_sanitize_retailer_product_url("https://www.amazon.in/bad path with spaces", "amazon") is None


def test_retailer_fallback_search_url_preserves_full_query_and_variant():
    """Verify that fallback search URLs preserve brand, model, and variants with proper URL encoding."""
    from app.core.retailer_allowlist import (
        build_product_query_for_search,
        build_retailer_fallback_search_url,
    )

    # 1. iPhone 15
    q1 = "iPhone 15"
    assert build_product_query_for_search(q1) == "iPhone 15"
    amz_url1 = build_retailer_fallback_search_url("amazon", q1)
    fk_url1 = build_retailer_fallback_search_url("flipkart", q1)
    assert amz_url1 == "https://www.amazon.in/s?k=iPhone+15"
    assert fk_url1 == "https://www.flipkart.com/search?q=iPhone+15"

    # 2. iPhone 15 with storage and color variant
    q2 = "Apple iPhone 15 (128 GB) - Black"
    assert "128 GB" in build_product_query_for_search(q2)
    amz_url2 = build_retailer_fallback_search_url("amazon", q2)
    assert "128+GB" in amz_url2 or "128+GB" in amz_url2.replace("+", " ")
    assert amz_url2.startswith("https://www.amazon.in/s?k=")

    # 3. Moto G96
    q3 = "Moto G96"
    assert build_product_query_for_search(q3) == "Moto G96"
    amz_url3 = build_retailer_fallback_search_url("amazon", q3)
    fk_url3 = build_retailer_fallback_search_url("flipkart", q3)
    assert amz_url3 == "https://www.amazon.in/s?k=Moto+G96"
    assert fk_url3 == "https://www.flipkart.com/search?q=Moto+G96"

    # 4. Moto G96 5G 256GB
    q4 = "Motorola Moto G96 5G 256GB"
    amz_url4 = build_retailer_fallback_search_url("amazon", q4)
    fk_url4 = build_retailer_fallback_search_url("flipkart", q4)
    assert "G96" in amz_url4 and "256GB" in amz_url4
    assert "G96" in fk_url4 and "256GB" in fk_url4
    assert not any(c.isspace() for c in amz_url4)
    assert not any(c.isspace() for c in fk_url4)

    # 5. Unknown retailer returns None (never a made-up URL)
    assert build_retailer_fallback_search_url("fake_store", "iPhone 15") is None


def test_serpapi_direct_product_url_versus_fallback_search_url():
    """Verify that SerpApi direct product URLs are preserved, whereas Google Shopping
    internal search URLs fall back to verified retailer search URLs."""
    from decimal import Decimal
    from unittest.mock import patch, MagicMock
    from app.services.link_search import _query_serpapi_shopping

    mock_items = [
        # Amazon has an authentic direct HTTPS product URL
        {
            "position": 1,
            "title": "Apple iPhone 15 (128 GB)",
            "source": "Amazon.in",
            "price": "₹69,900.00",
            "extracted_price": 69900.0,
            "link": "https://www.amazon.in/Apple-iPhone-15-128-GB/dp/B0CHX1W1XY",
            "rating": 4.6,
        },
        # Flipkart only has a Google Shopping search aggregation URL
        {
            "position": 2,
            "title": "Apple iPhone 15 (128 GB)",
            "source": "Flipkart",
            "price": "₹70,900.00",
            "extracted_price": 70900.0,
            "link": None,
            "product_link": "https://www.google.co.in/search?ibp=oshop&q=iPhone 15&prds=catalogid:123",
            "rating": 4.5,
        },
    ]

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"shopping_results": mock_items}

    with patch("httpx.Client.get", return_value=mock_response):
        res = _query_serpapi_shopping(
            user_input="iPhone 15",
            extracted_title="iPhone 15",
            is_url=False,
            source_platform="Keyword Query",
            api_key="test_api_key",
            currency="INR",
            trusted_retailers=["amazon", "flipkart"],
        )

        assert res is not None
        amz = next(s for s in res.stores if s.store_code == "amazon")
        fk = next(s for s in res.stores if s.store_code == "flipkart")

        # Amazon must retain its authentic direct product URL
        assert amz.is_direct_url is True
        assert amz.store_url == "https://www.amazon.in/Apple-iPhone-15-128-GB/dp/B0CHX1W1XY"

        # Flipkart must NOT be given the Google Shopping search URL
        assert fk.is_direct_url is False
        assert "google.co.in" not in fk.store_url
        assert fk.store_url == "https://www.flipkart.com/search?q=iPhone+15"
        assert not any(c.isspace() for c in fk.store_url)


def test_shortened_url_amzn_in_0fhQ0IWO_unresolvable_rejects_d_and_shows_clear_error(client: TestClient):
    """Regression test: submitting an unresolvable short link like 'https://amzn.in/d/0fhQ0IWO'
    must NEVER extract 'd' as product title, must never query for 'd', must return clear error
    with an option to search by product name, and must not create fake DB trajectory or savings."""
    from app.services.safe_url_resolver import clear_mock_resolutions
    clear_mock_resolutions()

    short_link = "https://amzn.in/d/0fhQ0IWO"

    # Direct unit check on title extraction
    from app.services.link_search import extract_product_title
    res = extract_product_title(short_link)
    assert res.title != "d", "Must never return single character 'd' as product title!"
    assert res.title == "Unresolved Product Link"
    assert res.is_url is True
    assert res.resolution_error is not None

    # API Endpoint check
    response = client.get(f"/api/v1/search/universal?query={short_link}")
    assert response.status_code == 200
    data = response.json()

    assert data["extracted_title"] != "d"
    assert data["extracted_title"] == "Unresolved Product Link"
    assert data["has_reliable_match"] is False
    assert data["lowest_price"] is None
    assert data["highest_price"] is None
    assert data["max_savings"] is None
    assert data["savings_percentage"] == 0.0
    assert data["ai_insight"] is None, "AI forecast must be hidden when product cannot be verified"
    assert data["stores"] == [], "Must not return fake or unrelated quotes for 'd'"
    assert "Please search by product name" in data["recommendation_summary"]
    assert data["suggested_action"] == "Search by product name"
    assert data["db_updated"] is False, "Must not persist unresolved link into catalog"


def test_shortened_url_resolves_safely_and_extracts_product_model_and_variant():
    """Verify that a resolvable shortened retailer link safely follows redirects,
    extracts the descriptive product name, model, and variant, and never extracts 'd'."""
    from app.services.safe_url_resolver import (
        register_mock_resolution,
        clear_mock_resolutions,
        extract_product_info_from_resolved_url,
    )
    from app.services.link_search import extract_product_title

    clear_mock_resolutions()
    short_url = "https://amzn.in/d/0fhQ0IWO"
    resolved_destination = "https://www.amazon.in/Apple-iPhone-15-128-GB/dp/B0CHX1W1XY?th=1"
    sample_html = "<title>Apple iPhone 15 (128 GB) - Black : Amazon.in: Electronics</title>"

    register_mock_resolution(
        short_url,
        final_url=resolved_destination,
        html_content=sample_html,
    )

    try:
        # Unit check on info extractor
        t, m, v = extract_product_info_from_resolved_url(resolved_destination, sample_html)
        assert t == "Apple iPhone 15 (128 GB) - Black"
        assert m == "iPhone 15"
        assert "128GB" in v

        # Integration check on extract_product_title
        extracted = extract_product_title(short_url)
        assert extracted.title != "d"
        assert "iPhone 15" in extracted.title
        assert extracted.is_url is True
        assert extracted.source_platform == "Amazon India"
        assert extracted.resolved_url == resolved_destination
        assert extracted.resolution_error is None
    finally:
        clear_mock_resolutions()


def test_cross_category_and_unrelated_listings_rejection():
    """Verify that comparisons reject products from differing categories (e.g. running shoes, cooktops)
    when searching for a phone (iPhone 15)."""
    from app.services.link_search import is_unrelated_or_parts_item, detect_product_category

    assert detect_product_category("Apple iPhone 15 128GB") == "smartphone"
    assert detect_product_category("Puma Nitro Running Shoes") == "apparel_shoes"
    assert detect_product_category("Prestige Induction Cooktop 2000W") == "appliance"
    assert detect_product_category("HP Pavilion Gaming Laptop") == "laptop"

    phone_query = "Apple iPhone 15 128GB"

    # Cross-category items must be rejected
    is_bad1, r1 = is_unrelated_or_parts_item("Puma Nitro Men's Running Shoes", "Amazon India", phone_query)
    assert is_bad1 is True
    assert "Cross-category conflict" in r1

    is_bad2, r2 = is_unrelated_or_parts_item("Prestige Induction Cooktop 2000W", "Flipkart", phone_query)
    assert is_bad2 is True
    assert "Cross-category conflict" in r2

    is_bad3, r3 = is_unrelated_or_parts_item("HP Pavilion 15.6 inch FHD Laptop", "Amazon India", phone_query)
    assert is_bad3 is True
    assert "Cross-category conflict" in r3

    # Accessories must be rejected
    is_bad4, r4 = is_unrelated_or_parts_item("Liquid Silicone Case for iPhone 15", "Amazon India", phone_query)
    assert is_bad4 is True
    assert "accessory" in r4.lower() or "passing mention" in r4.lower()

    # Genuine matching phone must be accepted
    is_bad5, _ = is_unrelated_or_parts_item("Apple iPhone 15 (128 GB) - Blue", "Flipkart", phone_query)
    assert is_bad5 is False


def test_ssrf_protection_blocks_private_and_local_network_addresses(client: TestClient):
    """Verify that private and loopback IP addresses (SSRF targets) are blocked immediately."""
    from app.services.safe_url_resolver import validate_url_for_ssrf

    forbidden_urls = [
        "http://127.0.0.1/latest/meta-data",
        "http://localhost:8000/internal",
        "http://169.254.169.254/latest/meta-data",
        "http://10.0.0.1/admin",
        "http://192.168.1.1/router",
        "http://[::1]/secret",
    ]

    for f_url in forbidden_urls:
        safe, err = validate_url_for_ssrf(f_url)
        assert safe is False, f"URL {f_url} should have been blocked by SSRF protection!"
        assert "blocked" in err.lower() or "forbidden" in err.lower() or "private" in err.lower() or "localhost" in err.lower()

        # Check API response
        resp = client.get(f"/api/v1/search/universal?query={f_url}")
        assert resp.status_code == 200
        d = resp.json()
        assert d["has_reliable_match"] is False
        assert d["lowest_price"] is None
        assert "Security rejection" in (d.get("resolution_error") or "") or "blocked" in (d.get("resolution_error") or "").lower()
        assert d["stores"] == []


def test_forecast_and_savings_hidden_when_listings_not_comparable():
    """Verify that when only 1 listing is found or listings have differing variants/conditions,
    no best deal, savings calculation, or forecast is claimed."""
    from decimal import Decimal
    from unittest.mock import patch, MagicMock
    from app.services.link_search import _query_serpapi_shopping

    # Single verified listing for Moto G96
    mock_items = [
        {
            "position": 1,
            "title": "Motorola Moto G96 5G (128 GB)",
            "source": "Flipkart",
            "price": "₹16,999.00",
            "extracted_price": 16999.0,
            "link": "https://www.flipkart.com/motorola-moto-g96-5g-128-gb",
            "in_stock": True,
        }
    ]

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"shopping_results": mock_items}

    with patch("httpx.Client.get", return_value=mock_response):
        res = _query_serpapi_shopping(
            user_input="Moto G96",
            extracted_title="Moto G96",
            is_url=False,
            source_platform="Keyword Query",
            api_key="test_key",
            currency="INR",
            trusted_retailers=["amazon", "flipkart"],
        )

        assert res is not None
        assert res.has_reliable_match is True
        assert res.is_comparable_comparison is False, "Single listing cannot be a comparable comparison"
        assert res.max_savings is None, "Must not claim savings for a single listing"
        assert res.savings_percentage == 0.0
        assert not any(s.is_lowest for s in res.stores), "Must not mark single listing as best deal"
        assert res.ai_insight is None, "Forecast must be hidden when only 1 listing is present"
        assert "At least two comparable listings" in res.recommendation_summary


def test_full_amazon_url_extracts_product_name_not_retailer_domain(client: TestClient):
    """Regression test: submitting a full Amazon product URL like
    'https://www.amazon.in/Apple-iPhone-15-128-GB/dp/B0CHX1W1XY'
    must identify the retailer as 'Amazon India', extract 'Apple iPhone 15 128 GB'
    as the product title, and MUST NEVER search SerpApi for 'amazon.in' or 'www.amazon.in'."""
    from unittest.mock import patch, MagicMock
    from app.services.link_search import extract_product_title, search_and_compare_product
    from app.core.config import settings

    url = "https://www.amazon.in/Apple-iPhone-15-128-GB/dp/B0CHX1W1XY"

    # 1. Direct title extraction check
    extracted = extract_product_title(url)
    assert extracted.title == "Apple iPhone 15 128 GB"
    assert extracted.title != "amazon.in"
    assert extracted.title != "www.amazon.in"
    assert extracted.source_platform == "Amazon India"
    assert extracted.is_url is True

    # 2. End-to-end SerpApi query check: verify query sent to SerpApi contains 'iPhone 15' and NEVER 'amazon.in'
    mock_items = [
        {
            "position": 1,
            "title": "Apple iPhone 15 (128 GB) - Black",
            "source": "Amazon India",
            "price": "₹64,900.00",
            "extracted_price": 64900.0,
            "link": "https://www.amazon.in/dp/B0CHX1W1XY",
        },
        {
            "position": 2,
            "title": "Apple iPhone 15 (128 GB) - Blue",
            "source": "Flipkart",
            "price": "₹65,999.00",
            "extracted_price": 65999.0,
            "link": "https://www.flipkart.com/apple-iphone-15-128-gb",
        },
    ]

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"shopping_results": mock_items}

    with patch.object(settings, "serpapi_api_key", "test_key"), \
         patch("httpx.Client.get", return_value=mock_resp) as mock_get:
        res = search_and_compare_product(url)

        assert res.extracted_title == "Apple iPhone 15 128 GB"
        assert res.has_reliable_match is True
        assert res.lowest_price is not None
        assert mock_get.called

        for call_args in mock_get.call_args_list:
            params = call_args.kwargs.get("params") or (call_args.args[1] if len(call_args.args) > 1 else {})
            q = params.get("q", "")
            assert "amazon.in" not in q.lower(), f"Disallowed domain 'amazon.in' found in SerpApi query: '{q}'"
            assert "www.amazon.in" not in q.lower()
            assert "iphone 15" in q.lower(), f"Expected product 'iPhone 15' in SerpApi query, got: '{q}'"


def test_full_flipkart_url_extracts_product_name_not_retailer_domain(client: TestClient):
    """Regression test: submitting a full Flipkart product URL like
    'https://www.flipkart.com/apple-iphone-15-black-128-gb/p/itm6ac6485515ae4'
    must identify the retailer as 'Flipkart', extract 'Apple iPhone 15 Black 128 GB'
    as the product title, and MUST NEVER search SerpApi for 'flipkart.com'."""
    from unittest.mock import patch, MagicMock
    from app.services.link_search import extract_product_title, search_and_compare_product
    from app.core.config import settings

    url = "https://www.flipkart.com/apple-iphone-15-black-128-gb/p/itm6ac6485515ae4"

    extracted = extract_product_title(url)
    assert "iphone 15" in extracted.title.lower()
    assert "flipkart.com" not in extracted.title.lower()
    assert extracted.source_platform == "Flipkart"
    assert extracted.is_url is True

    mock_items = [
        {
            "position": 1,
            "title": "Apple iPhone 15 (128 GB) - Black",
            "source": "Flipkart",
            "price": "₹64,900.00",
            "extracted_price": 64900.0,
            "link": url,
        },
        {
            "position": 2,
            "title": "Apple iPhone 15 (128 GB) - Blue",
            "source": "Amazon India",
            "price": "₹65,999.00",
            "extracted_price": 65999.0,
            "link": "https://www.amazon.in/dp/B0CHX1W1XY",
        },
    ]

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"shopping_results": mock_items}

    with patch.object(settings, "serpapi_api_key", "test_key"), \
         patch("httpx.Client.get", return_value=mock_resp) as mock_get:
        res = search_and_compare_product(url)

        assert "iphone 15" in res.extracted_title.lower()
        assert res.has_reliable_match is True
        assert mock_get.called

        for call_args in mock_get.call_args_list:
            params = call_args.kwargs.get("params") or {}
            q = params.get("q", "")
            assert "flipkart.com" not in q.lower(), f"Disallowed domain 'flipkart.com' found in SerpApi query: '{q}'"
            assert "iphone 15" in q.lower(), f"Expected product 'iPhone 15' in SerpApi query, got: '{q}'"


def test_full_amazon_asin_url_extracts_product_name_not_dp_or_domain(client: TestClient):
    """Regression test: submitting an Amazon product URL with only an ASIN like
    'https://www.amazon.in/dp/B0CHX1W1XY'
    must identify the product from catalog metadata and MUST NEVER search for 'dp' or 'amazon.in'."""
    from unittest.mock import patch, MagicMock
    from app.services.link_search import extract_product_title, search_and_compare_product
    from app.core.config import settings

    url = "https://www.amazon.in/dp/B0CHX1W1XY"

    extracted = extract_product_title(url)
    assert extracted.title != "dp", "Must never return path fragment 'dp' as product title!"
    assert "amazon.in" not in extracted.title.lower()
    assert "iPhone 15" in extracted.title
    assert extracted.source_platform == "Amazon India"

    mock_items = [
        {
            "position": 1,
            "title": "Apple iPhone 15 (128 GB) - Black",
            "source": "Amazon India",
            "price": "₹64,900.00",
            "extracted_price": 64900.0,
            "link": url,
        },
        {
            "position": 2,
            "title": "Apple iPhone 15 (128 GB) - Black",
            "source": "Flipkart",
            "price": "₹65,999.00",
            "extracted_price": 65999.0,
            "link": "https://www.flipkart.com/apple-iphone-15-black-128-gb/p/itm6ac6485515ae4",
        },
    ]

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"shopping_results": mock_items}

    with patch.object(settings, "serpapi_api_key", "test_key"), \
         patch("httpx.Client.get", return_value=mock_resp) as mock_get:
        res = search_and_compare_product(url)

        assert "iphone 15" in res.extracted_title.lower()
        for call_args in mock_get.call_args_list:
            params = call_args.kwargs.get("params") or {}
            q = params.get("q", "")
            assert "amazon.in" not in q.lower()
            assert q.strip().lower() != "dp"
            assert "iphone 15" in q.lower()


def test_bare_retailer_domains_halt_without_serpapi_search(client: TestClient):
    """Regression test: bare retailer domains or non-product paths (e.g. 'https://www.amazon.in',
    'https://www.flipkart.com', 'https://www.amazon.in/dp/') must stop gracefully with a clear message
    asking the user to enter the product name, and must NEVER invoke SerpApi with retailer domains."""
    from unittest.mock import patch
    from app.services.link_search import search_and_compare_product
    from app.core.config import settings

    bare_urls = [
        "https://www.amazon.in",
        "https://www.amazon.in/",
        "https://www.flipkart.com",
        "https://www.flipkart.com/",
        "https://www.amazon.in/dp/",
    ]

    for u in bare_urls:
        with patch.object(settings, "serpapi_api_key", "test_key"), \
             patch("httpx.Client.get") as mock_get:
            res = search_and_compare_product(u)

            assert res.has_reliable_match is False
            assert res.lowest_price is None
            assert res.stores == []
            assert "Please search by product name" in res.recommendation_summary or "Please enter the product name" in res.recommendation_summary
            assert res.suggested_action == "Search by product name"
            # SerpApi must NEVER be called
            assert not mock_get.called, f"SerpApi was unexpectedly called for bare retailer link '{u}'"


def test_shortened_amazon_url_resolves_and_searches_product_not_shortlink_domain():
    """Regression test: submitting shortened Amazon link resolves to real product URL,
    extracts the product name, and queries SerpApi with the product name (never 'amzn.in' or 'd')."""
    from unittest.mock import patch, MagicMock
    from app.services.safe_url_resolver import register_mock_resolution, clear_mock_resolutions
    from app.services.link_search import extract_product_title, search_and_compare_product
    from app.core.config import settings

    clear_mock_resolutions()
    short_link = "https://amzn.in/d/0fhQ0IWO"
    full_dest = "https://www.amazon.in/Apple-iPhone-15-128-GB/dp/B0CHX1W1XY"
    register_mock_resolution(short_link, full_dest, "<html><title>Apple iPhone 15 128 GB</title></html>")

    try:
        extracted = extract_product_title(short_link)
        assert extracted.title == "Apple iPhone 15 128 GB"
        assert extracted.title != "d"
        assert extracted.title != "amzn.in"
        assert extracted.source_platform == "Amazon India"

        mock_items = [
            {
                "position": 1,
                "title": "Apple iPhone 15 (128 GB) - Black",
                "source": "Amazon India",
                "price": "₹64,900.00",
                "extracted_price": 64900.0,
                "link": full_dest,
            },
            {
                "position": 2,
                "title": "Apple iPhone 15 (128 GB) - Blue",
                "source": "Flipkart",
                "price": "₹65,999.00",
                "extracted_price": 65999.0,
                "link": "https://www.flipkart.com/apple-iphone-15-128-gb",
            },
        ]

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"shopping_results": mock_items}

        with patch.object(settings, "serpapi_api_key", "test_key"), \
             patch("httpx.Client.get", return_value=mock_resp) as mock_get:
            res = search_and_compare_product(short_link)

            assert res.extracted_title == "Apple iPhone 15 128 GB"
            assert res.has_reliable_match is True
            assert mock_get.called

            for call_args in mock_get.call_args_list:
                params = call_args.kwargs.get("params") or {}
                q = params.get("q", "")
                assert "amzn.in" not in q.lower()
                assert "amazon.in" not in q.lower()
                assert q.strip().lower() != "d"
                assert "iphone 15" in q.lower()
    finally:
        clear_mock_resolutions()


def test_disallowed_search_query_guards():
    """Verify that is_disallowed_search_query detects and rejects domains, hostnames, and fragments."""
    from app.services.safe_url_resolver import is_disallowed_search_query

    disallowed = [
        "amazon.in",
        "www.amazon.in",
        "flipkart.com",
        "www.flipkart.com",
        "amzn.in",
        "croma.com",
        "dp",
        "d",
        "p",
        "gp",
        "product",
        "buy",
        "item",
        "unresolved product link",
        "unknown product",
    ]
    for term in disallowed:
        assert is_disallowed_search_query(term) is True, f"'{term}' should be recognized as disallowed search query"

    allowed = [
        "iPhone 15",
        "Apple iPhone 15 128 GB",
        "Moto G96",
        "Motorola Moto G 96",
        "Sony WH-1000XM4",
        "Samsung Galaxy S24",
    ]
    for term in allowed:
        assert is_disallowed_search_query(term) is False, f"'{term}' should be recognized as a valid search query"


def test_shortened_flipkart_url_dl_flipkart_com_4ibkdsuuuN_resolves_and_extracts_product():
    """Regression test: submitting Flipkart app short link 'https://dl.flipkart.com/s/4ibkdsuuuN'
    resolves safely, avoids false-positive SSRF rejection on NAT64 carrier addresses,
    extracts 'Motorola Edge 70 Pro 256 GB', and performs valid cross-store price comparison."""
    from unittest.mock import patch
    from app.services.safe_url_resolver import register_mock_resolution, clear_mock_resolutions
    from app.services.link_search import extract_product_title, search_and_compare_product

    clear_mock_resolutions()
    short_link = "https://dl.flipkart.com/s/4ibkdsuuuN"
    dest_url = "https://www.flipkart.com/motorola-edge-70-pro-tailored-fabric-pantone-titan-blue-256-gb/p/itmabaee92c5d0da?pid=MOBHN9734ZPCKBAC"

    register_mock_resolution(
        short_link,
        final_url=dest_url,
        html_content="<title>Motorola Edge 70 Pro (256 GB) Online at Best Price in India | Flipkart.com</title>",
    )

    try:
        extracted = extract_product_title(short_link)
        assert extracted.is_url is True
        assert extracted.source_platform == "Flipkart"
        assert extracted.title != "Unresolved Product Link"
        assert "Motorola Edge 70 Pro" in extracted.title
        assert "flipkart.com" not in extracted.title.lower()
        assert "dl" not in extracted.title.lower().split()
        assert "s" not in extracted.title.lower().split()

        res = search_and_compare_product(short_link)
        assert res.has_reliable_match is True
        assert res.lowest_price is not None
        assert "Motorola Edge 70 Pro" in res.extracted_title
        assert any("flipkart" in s.store_code.lower() for s in res.stores)
    finally:
        clear_mock_resolutions()


def test_nat64_and_ipv4_mapped_ipv6_ssrf_safety():
    """Verify that RFC 6052 NAT64 and IPv4-mapped IPv6 addresses are safely inspected for SSRF:
    public translated IPs are permitted while private/loopback/cloud metadata destinations are blocked."""
    from app.services.safe_url_resolver import is_ip_safe_and_public

    # Public carrier NAT64 (Akamai / Flipkart translated edge)
    assert is_ip_safe_and_public("64:ff9b::a335:4d3e") is True

    # Malicious loopback or private addresses synthesized via NAT64 must be blocked
    assert is_ip_safe_and_public("64:ff9b::7f00:1") is False     # 127.0.0.1
    assert is_ip_safe_and_public("64:ff9b::a9fe:a9fe") is False  # 169.254.169.254 (AWS metadata)
    assert is_ip_safe_and_public("64:ff9b::c0a8:101") is False   # 192.168.1.1
    assert is_ip_safe_and_public("64:ff9b::0a00:0001") is False  # 10.0.0.1

    # IPv4-mapped IPv6 addresses
    assert is_ip_safe_and_public("::ffff:127.0.0.1") is False    # Localhost
    assert is_ip_safe_and_public("::ffff:169.254.169.254") is False
    assert is_ip_safe_and_public("::ffff:163.53.77.62") is True  # Public Flipkart Akamai IP

















