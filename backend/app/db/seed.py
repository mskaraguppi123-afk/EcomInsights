from datetime import datetime
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models.price_observation import PriceObservation
from app.models.product import Product

try:
    from ecominsights_ml.data import load_sample_prices
except ImportError:
    from csv import DictReader

    def load_sample_prices() -> list[dict[str, str]]:
        csv_path = Path(__file__).resolve().parents[3] / "ml" / "data" / "sample_prices.csv"
        with csv_path.open(newline="", encoding="utf-8") as csv_file:
            return list(DictReader(csv_file))


def seed_sample_data(db: Session, force_reset: bool = False) -> dict[str, int]:
    """Seed synthetic sample products and price observations into the database.

    If force_reset is True, existing observations and products are deleted first.
    Otherwise this operation is idempotent: existing records are not duplicated.
    """
    if force_reset:
        db.query(PriceObservation).delete()
        db.query(Product).delete()
        db.commit()

    rows = load_sample_prices()
    products_created = 0
    observations_created = 0


    for row in rows:
        name = row["product_name"].strip()
        category = row.get("category", "").strip() or None
        source_label = row.get("source_label", "sample").strip()
        currency = row.get("currency", "INR").strip()
        price = Decimal(row["price"].strip())
        observed_at = datetime.fromisoformat(row["observed_at"].strip())

        # Find or create Product
        product = db.scalars(select(Product).where(Product.name == name)).first()
        if not product:
            product = Product(name=name, category=category)
            db.add(product)
            db.flush()  # populate product.id
            products_created += 1

        # Check if this exact observation already exists
        existing_obs = db.scalars(
            select(PriceObservation).where(
                PriceObservation.product_id == product.id,
                PriceObservation.observed_at == observed_at,
                PriceObservation.price == price,
            )
        ).first()

        if not existing_obs:
            observation = PriceObservation(
                product_id=product.id,
                source_label=source_label,
                price=price,
                currency=currency,
                observed_at=observed_at,
            )
            db.add(observation)
            observations_created += 1

    db.commit()
    return {
        "products_created": products_created,
        "observations_created": observations_created,
    }


def main() -> None:
    """Run seeding directly from the command line."""
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        result = seed_sample_data(db)
        print(
            f"Database seeded successfully: "
            f"{result['products_created']} products, "
            f"{result['observations_created']} observations created."
        )


if __name__ == "__main__":
    main()
