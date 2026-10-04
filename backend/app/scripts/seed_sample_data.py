"""Load the local synthetic sample CSV into PostgreSQL (safe to run repeatedly)."""

import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select

PROJECT_ROOT = Path(__file__).resolve().parents[3]
ML_SOURCE = PROJECT_ROOT / "ml" / "src"
sys.path.insert(0, str(ML_SOURCE))

from ecominsights_ml.data import load_sample_prices  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.models.price_observation import PriceObservation  # noqa: E402
from app.models.product import Product  # noqa: E402


def seed_sample_data() -> tuple[int, int]:
    """Insert missing sample products and observations; preserve existing records."""
    Base.metadata.create_all(bind=engine)
    rows = load_sample_prices()
    products_added = 0
    observations_added = 0

    with SessionLocal.begin() as db:
        for row in rows:
            name = row["product_name"].strip()
            category = row["category"].strip() or None
            product = db.scalar(
                select(Product).where(Product.name == name, Product.category == category)
            )
            if product is None:
                product = Product(name=name, category=category)
                db.add(product)
                db.flush()
                products_added += 1

            observed_at = datetime.fromisoformat(row["observed_at"])
            existing_observation = db.scalar(
                select(PriceObservation.id).where(
                    PriceObservation.product_id == product.id,
                    PriceObservation.source_label == row["source_label"],
                    PriceObservation.observed_at == observed_at,
                )
            )
            if existing_observation is None:
                db.add(
                    PriceObservation(
                        product_id=product.id,
                        source_label=row["source_label"],
                        currency=row["currency"],
                        price=Decimal(row["price"]),
                        observed_at=observed_at,
                    )
                )
                observations_added += 1

    return products_added, observations_added


if __name__ == "__main__":
    product_count, observation_count = seed_sample_data()
    print(f"Added {product_count} products and {observation_count} price observations.")
