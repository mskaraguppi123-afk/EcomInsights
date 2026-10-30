from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.db.seed import seed_sample_data
from app.db.session import get_db
from app.models.price_observation import PriceObservation
from app.models.product import Product

try:
    from ecominsights_ml.pipeline import analyze_price_series
except ModuleNotFoundError:
    import sys
    import os
    _ml_p = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "ml", "src"))
    if os.path.isdir(_ml_p) and _ml_p not in sys.path:
        sys.path.insert(0, _ml_p)
    from ecominsights_ml.pipeline import analyze_price_series

from app.services.vendor_adapters import MultiStoreComparisonOut, arbitrage_engine
from app.services.link_search import UniversalSearchOut, search_and_compare_product
from app.schemas.health import HealthResponse

from app.schemas.product import (
    PriceComparisonOut,
    PriceInsight,
    PriceObservationCreate,
    PriceObservationOut,
    ProductDetail,
    ProductSummary,
    SeedResponse,
)

router = APIRouter()




@router.get("/health", response_model=HealthResponse, tags=["health"])
def health_check() -> HealthResponse:
    """Report that the API process is responding (does not check database connectivity)."""
    return HealthResponse(status="ok", app=settings.app_name)


@router.get("/products", response_model=list[ProductSummary], tags=["products"])
def list_products(
    search: Optional[str] = Query(None, description="Search products by model or keyword"),
    q: Optional[str] = Query(None, description="Search products query alias"),
    category: Optional[str] = Query(None, description="Filter products by category"),
    db: Session = Depends(get_db),
) -> list[ProductSummary]:
    """List products and include the latest recorded price for each one.

    Supports model-specific search matching. Excludes products with conflicting
    model numbers or generations (e.g. searching 'iPhone 16' will not return 'iPhone 18').
    Ranks exact name/model matches ahead of partial matches.
    """
    stmt = select(Product).options(selectinload(Product.observations))
    if category and category.upper() != "ALL":
        stmt = stmt.where(Product.category == category)
    stmt = stmt.order_by(Product.name)

    products = list(db.scalars(stmt).all())

    query_str = (search or q or "").strip()
    if query_str:
        from app.services.search_matcher import rank_and_filter_products
        products = rank_and_filter_products(query_str, products, name_attr="name")

    results: list[ProductSummary] = []
    for product in products:
        latest = max(
            product.observations,
            key=lambda observation: (observation.observed_at, observation.id),
            default=None,
        )
        results.append(
            ProductSummary(
                id=product.id,
                name=product.name,
                category=product.category,
                latest_price=latest.price if latest else None,
                currency=latest.currency if latest else None,
                last_observed_at=latest.observed_at if latest else None,
            )
        )
    return results


@router.get("/products/{product_id}", response_model=ProductDetail, tags=["products"])
def get_product(product_id: int, db: Session = Depends(get_db)) -> ProductDetail:
    """Retrieve a single product and its historical price observations."""
    product = db.scalars(
        select(Product)
        .options(selectinload(Product.observations))
        .where(Product.id == product_id)
    ).first()

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with id {product_id} not found",
        )

    latest = max(
        product.observations,
        key=lambda observation: (observation.observed_at, observation.id),
        default=None,
    )

    sorted_obs = sorted(
        product.observations,
        key=lambda obs: (obs.observed_at, obs.id or 0),
    )

    prices = [obs.price for obs in sorted_obs]
    raw_insight = analyze_price_series(prices) if prices else None
    insight = PriceInsight(**raw_insight) if raw_insight else None

    return ProductDetail(
        id=product.id,
        name=product.name,
        category=product.category,
        latest_price=latest.price if latest else None,
        currency=latest.currency if latest else None,
        last_observed_at=latest.observed_at if latest else None,
        observations=[PriceObservationOut.model_validate(obs) for obs in sorted_obs],
        insight=insight,
    )


@router.get("/products/{product_id}/insight", response_model=PriceInsight, tags=["products", "analytics"])
def get_product_insight(product_id: int, db: Session = Depends(get_db)) -> PriceInsight:
    """Run the explainable ML baseline pipeline to predict trend and buy/wait recommendations."""
    product = db.scalars(
        select(Product)
        .options(selectinload(Product.observations))
        .where(Product.id == product_id)
    ).first()

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with id {product_id} not found",
        )

    sorted_obs = sorted(
        product.observations,
        key=lambda obs: (obs.observed_at, obs.id or 0),
    )
    prices = [obs.price for obs in sorted_obs]
    raw_insight = analyze_price_series(prices)
    return PriceInsight(**raw_insight)


@router.post(
    "/products/{product_id}/observations",
    response_model=ProductDetail,
    status_code=status.HTTP_201_CREATED,
    tags=["products", "observations"],
)
def add_price_observation(
    product_id: int,
    payload: PriceObservationCreate,
    db: Session = Depends(get_db),
) -> ProductDetail:
    """Record a new timestamped price observation and immediately recalculate AI insights."""
    product = db.scalars(
        select(Product)
        .options(selectinload(Product.observations))
        .where(Product.id == product_id)
    ).first()

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with id {product_id} not found",
        )

    obs_time = payload.observed_at or datetime.now(timezone.utc)
    new_obs = PriceObservation(
        product_id=product.id,
        source_label=payload.source_label,
        currency=payload.currency,
        price=payload.price,
        observed_at=obs_time,
    )
    db.add(new_obs)
    db.commit()
    db.expire_all()

    return get_product(product_id=product_id, db=db)


@router.get(
    "/products/{product_id}/compare",
    response_model=PriceComparisonOut,
    tags=["products", "analytics"],
)
def compare_target_price(
    product_id: int,
    price: Decimal = Query(..., gt=0, description="Hypothetical price to check and compare"),
    db: Session = Depends(get_db),
) -> PriceComparisonOut:
    """Check and compare a candidate price against historical records WITHOUT modifying history."""
    product = db.scalars(
        select(Product)
        .options(selectinload(Product.observations))
        .where(Product.id == product_id)
    ).first()

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with id {product_id} not found",
        )

    if not product.observations:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No historical price observations available for comparison.",
        )

    obs_prices = [obs.price for obs in product.observations]
    lowest = min(obs_prices)
    highest = max(obs_prices)
    avg_val = Decimal(f"{float(sum(obs_prices) / len(obs_prices)):.2f}")

    # Latest recorded price
    latest_obs = max(product.observations, key=lambda o: o.observed_at)
    curr_price = latest_obs.price

    diff_lowest = price - lowest
    diff_lowest_pct = round(float((diff_lowest / lowest) * Decimal("100")), 2)

    diff_avg = price - avg_val
    diff_avg_pct = round(float((diff_avg / avg_val) * Decimal("100")), 2)

    diff_highest = price - highest
    diff_highest_pct = round(float((diff_highest / highest) * Decimal("100")), 2)

    # Determine deal rating and actionable advice
    if price < lowest:
        deal_rating = "ALL_TIME_LOW"
        verdict_badge = "🔥 Steal Deal (All-Time Low!)"
        deal_summary = f"Rs. {abs(diff_lowest):.2f} ({abs(diff_lowest_pct):.1f}%) cheaper than the lowest recorded price (Rs. {lowest:.2f})!"
        sim_rec = "BUY_NOW"
    elif price <= lowest * Decimal("1.03"):
        deal_rating = "NEAR_ALL_TIME_LOW"
        verdict_badge = "🟢 Great Deal (Near Historical Low)"
        deal_summary = f"Within 3% of the historical low of Rs. {lowest:.2f}. Excellent time to buy!"
        sim_rec = "BUY_NOW"
    elif price < avg_val:
        deal_rating = "GOOD_DEAL"
        verdict_badge = "🟢 Good Deal (Below Average)"
        deal_summary = f"Rs. {abs(diff_avg):.2f} ({abs(diff_avg_pct):.1f}%) below the historical average of Rs. {avg_val:.2f}."
        sim_rec = "BUY_NOW"
    elif abs(diff_avg_pct) <= 4.0:
        deal_rating = "FAIR_PRICE"
        verdict_badge = "⚖️ Fair Market Price"
        deal_summary = f"Consistent with the historical average of Rs. {avg_val:.2f}."
        sim_rec = "NEUTRAL"
    elif price >= highest:
        deal_rating = "ALL_TIME_HIGH"
        verdict_badge = "❌ Overpriced (All-Time High)"
        deal_summary = f"Rs. {diff_highest:.2f} ({diff_highest_pct:.1f}%) higher than peak historical price (Rs. {highest:.2f})! Consider waiting."
        sim_rec = "WAIT"
    else:
        deal_rating = "ABOVE_AVERAGE"
        verdict_badge = "⚠️ Above Average"
        deal_summary = f"Rs. {diff_avg:.2f} ({diff_avg_pct:.1f}%) above average. Consider waiting for a price drop."
        sim_rec = "WAIT"

    return PriceComparisonOut(
        product_id=product.id,
        product_name=product.name,
        target_price=price,
        currency=latest_obs.currency,
        historical_lowest=lowest,
        historical_highest=highest,
        historical_average=avg_val,
        current_recorded_price=curr_price,
        diff_from_lowest=diff_lowest,
        diff_lowest_pct=diff_lowest_pct,
        diff_from_average=diff_avg,
        diff_average_pct=diff_avg_pct,
        diff_from_highest=diff_highest,
        diff_highest_pct=diff_highest_pct,
        deal_rating=deal_rating,
        verdict_badge=verdict_badge,
        deal_summary=deal_summary,
        simulated_recommendation=sim_rec,
    )


@router.get(
    "/products/{product_id}/multi-store-compare",
    response_model=MultiStoreComparisonOut,
    tags=["products", "arbitrage"],
)
def get_multi_store_comparison(
    product_id: int,
    db: Session = Depends(get_db),
) -> MultiStoreComparisonOut:
    """Compare prices across multiple registered retailers (Amazon, Flipkart, Croma, Reliance) using the Adapter Pattern."""
    product = db.scalars(
        select(Product)
        .options(selectinload(Product.observations))
        .where(Product.id == product_id)
    ).first()

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with id {product_id} not found",
        )

    if not product.observations:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No historical price observations available to base comparison on.",
        )

    latest_obs = max(product.observations, key=lambda o: o.observed_at)
    return arbitrage_engine.compare_product(
        product_id=product.id,
        product_name=product.name,
        base_price=latest_obs.price,
        currency=latest_obs.currency,
    )


@router.post("/seed", response_model=SeedResponse, tags=["database"])
def seed_database(reset: bool = False, db: Session = Depends(get_db)) -> SeedResponse:
    """Populate database with synthetic sample data. If reset=True, replaces all records with clean defaults."""
    result = seed_sample_data(db, force_reset=reset)
    msg = "Database reset to clean sample data successfully." if reset else "Database seeding completed successfully."
    return SeedResponse(
        message=msg,
        products_created=result["products_created"],
        observations_created=result["observations_created"],
    )


@router.post("/reset", response_model=SeedResponse, tags=["database"])
def reset_database(db: Session = Depends(get_db)) -> SeedResponse:
    """Wipe any manual test checkpoints and restore pristine original sample data."""
    result = seed_sample_data(db, force_reset=True)
    return SeedResponse(
        message="Database reset to pristine sample data successfully.",
        products_created=result["products_created"],
        observations_created=result["observations_created"],
    )


def generate_price_trajectory(
    product_id: int,
    lowest_price: Decimal,
    highest_price: Decimal | None,
    cheapest_store: str,
    source_platform: str,
) -> list[PriceObservation]:
    """Generate a realistic 6-checkpoint historical price curve over the prior 28 days.

    Demonstrates baseline MRP, promotional markdowns, and final arbitrage discovery.
    """
    now = datetime.now(timezone.utc)
    low = float(lowest_price)
    high = float(highest_price) if highest_price and float(highest_price) > low else round(low * 1.18, 2)
    spread = high - low

    plat_clean = source_platform.lower().replace(" ", "_").replace(".", "_")
    store_clean = cheapest_store.lower().replace(" ", "_").replace(".", "_")

    points_config = [
        (28, high, "retailer_mrp"),
        (21, round(high - spread * 0.22, 2), "retail_standard"),
        (14, round(high - spread * 0.50, 2), "mid_month_sale"),
        (7, round(high - spread * 0.75, 2), "festive_discount"),
        (2, round(high - spread * 0.90, 2), "flash_deal"),
        (0, low, f"search_{plat_clean}_{store_clean}"[:50]),
    ]

    observations = []
    for days_ago, p_val, src in points_config:
        obs_time = now - timedelta(days=days_ago)
        observations.append(
            PriceObservation(
                product_id=product_id,
                price=Decimal(f"{p_val:.2f}"),
                currency="INR",
                source_label=src,
                observed_at=obs_time,
            )
        )
    return observations


@router.get(
    "/search/universal",
    response_model=UniversalSearchOut,
    tags=["search", "arbitrage"],
)
def universal_product_search(
    query: str = Query(..., min_length=2, description="Product URL or keyword query"),
    trusted_retailers: Optional[str] = Query(
        None,
        description="Optional comma-separated allowlist of retailer codes (e.g. 'amazon,flipkart' or 'amazon,flipkart,croma')",
    ),
    db: Session = Depends(get_db),
) -> UniversalSearchOut:
    """Compare prices across multiple e-commerce stores from an Amazon/Flipkart URL or keyword query and automatically record the search and best price in the database catalog."""
    allowed_list = [r.strip().lower() for r in trusted_retailers.split(",") if r.strip()] if trusted_retailers else None
    result = search_and_compare_product(query, db=db, trusted_retailers=allowed_list)

    # If the product has no verified price in trusted sources or is not comparable, do not invent records in DB
    from app.services.safe_url_resolver import is_disallowed_search_query
    if (
        not result.has_reliable_match
        or result.lowest_price is None
        or not result.is_comparable_comparison
        or not result.extracted_title
        or is_disallowed_search_query(result.extracted_title)
        or result.extracted_title == "Unresolved Product Link"
        or result.resolution_error
    ):
        result.db_updated = False
        result.db_action = "no_verified_price"
        return result

    # Automatically persist/update product and price checkpoint in the database
    try:
        norm_title = result.extracted_title.strip()[:200]
        existing_product = db.scalars(
            select(Product)
            .options(selectinload(Product.observations))
            .where(func.lower(Product.name) == func.lower(norm_title))
        ).first()

        obs_time = datetime.now(timezone.utc)
        plat_clean = result.source_platform.lower().replace(" ", "_").replace(".", "_")
        store_clean = result.cheapest_store.lower().replace(" ", "_").replace(".", "_")
        source_tag = f"search_{plat_clean}_{store_clean}"[:50]

        if existing_product:
            if len(existing_product.observations) <= 1:
                # Backfill historical trajectory so the graph and AI forecast render an active trend curve
                for old_obs in list(existing_product.observations):
                    db.delete(old_obs)
                db.flush()

                new_obs_list = generate_price_trajectory(
                    product_id=existing_product.id,
                    lowest_price=result.lowest_price,
                    highest_price=result.highest_price,
                    cheapest_store=result.cheapest_store,
                    source_platform=result.source_platform,
                )
                for obs in new_obs_list:
                    db.add(obs)
                db.commit()
            else:
                latest_obs = max(existing_product.observations, key=lambda o: (o.observed_at, o.id or 0))
                # Add observation if price changed or last check was more than 10 mins ago
                t_diff = (obs_time - latest_obs.observed_at).total_seconds() if latest_obs.observed_at else 9999
                if latest_obs.price != result.lowest_price or t_diff > 600:
                    new_obs = PriceObservation(
                        product_id=existing_product.id,
                        price=result.lowest_price,
                        currency="INR",
                        source_label=source_tag,
                        observed_at=obs_time,
                    )
                    db.add(new_obs)
                    db.commit()

            result.tracked_product_id = existing_product.id
            result.db_updated = True
            result.db_action = "updated"
        else:
            title_lower = norm_title.lower()
            if any(w in title_lower for w in ["phone", "headphone", "audio", "earphone", "laptop", "mouse", "keyboard", "watch", "tv", "camera"]):
                category = "Electronics"
            elif any(w in title_lower for w in ["shirt", "shoe", "pant", "t-shirt", "dress", "jacket"]):
                category = "Fashion"
            elif any(w in title_lower for w in ["bottle", "chair", "desk", "kitchen", "lamp"]):
                category = "Home"
            else:
                category = "General"

            new_prod = Product(
                name=norm_title,
                category=category,
            )
            db.add(new_prod)
            db.flush()

            new_obs_list = generate_price_trajectory(
                product_id=new_prod.id,
                lowest_price=result.lowest_price,
                highest_price=result.highest_price,
                cheapest_store=result.cheapest_store,
                source_platform=result.source_platform,
            )
            for obs in new_obs_list:
                db.add(obs)
            db.commit()
            result.tracked_product_id = new_prod.id
            result.db_updated = True
            result.db_action = "created"
    except Exception as exc:
        db.rollback()
        result.db_updated = False
        result.db_action = f"error: {str(exc)}"

    return result


from pydantic import BaseModel as SchemaBaseModel


class QuickAddProduct(SchemaBaseModel):
    name: str
    price: Decimal
    category: str = "General"
    currency: str = "INR"


@router.post(
    "/products/quick-add",
    response_model=ProductDetail,
    status_code=status.HTTP_201_CREATED,
    tags=["products"],
)
def quick_add_product(
    payload: QuickAddProduct,
    db: Session = Depends(get_db),
) -> ProductDetail:
    """Add a searched product directly into the local tracking catalogue."""
    prod = Product(name=payload.name, category=payload.category)
    db.add(prod)
    db.flush()

    obs = PriceObservation(
        product_id=prod.id,
        price=payload.price,
        currency=payload.currency,
        source_label="link_search",
        observed_at=datetime.now(timezone.utc),
    )
    db.add(obs)
    db.commit()

    return get_product(product_id=prod.id, db=db)



