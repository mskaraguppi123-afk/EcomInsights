import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.seed import seed_sample_data
from app.db.session import get_db
import app.main as app_module

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








