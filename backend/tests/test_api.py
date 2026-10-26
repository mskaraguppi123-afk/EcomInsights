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
    assert data["cheapest_store"] == "Price unavailable"
    assert "Price unavailable" in data["recommendation_summary"]
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
            currency="INR"
        )

        assert res is not None
        assert res.has_reliable_match is True
        assert res.lowest_price == Decimal("78490.00")
        assert res.cheapest_store == "Croma"

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
            currency="INR"
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
        assert res.cheapest_store == "Price unavailable"
        assert len(res.stores) == 0










