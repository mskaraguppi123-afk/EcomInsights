from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class ProductSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    category: str | None
    latest_price: Decimal | None
    currency: str | None
    last_observed_at: datetime | None


class PriceObservationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source_label: str
    price: Decimal
    currency: str
    observed_at: datetime


class PriceObservationCreate(BaseModel):
    price: Decimal
    source_label: str = "manual"
    currency: str = "INR"
    observed_at: datetime | None = None


class PriceInsight(BaseModel):
    predicted_next_price: Decimal
    trend_direction: str
    change_percentage: float
    recommendation: str
    recommendation_reason: str
    lowest_price: Decimal
    highest_price: Decimal
    average_price: Decimal
    observation_count: int


class ProductDetail(ProductSummary):
    observations: list[PriceObservationOut] = []
    insight: PriceInsight | None = None


class PriceComparisonOut(BaseModel):
    product_id: int
    product_name: str
    target_price: Decimal
    currency: str
    historical_lowest: Decimal
    historical_highest: Decimal
    historical_average: Decimal
    current_recorded_price: Decimal | None
    diff_from_lowest: Decimal
    diff_lowest_pct: float
    diff_from_average: Decimal
    diff_average_pct: float
    diff_from_highest: Decimal
    diff_highest_pct: float
    deal_rating: str
    verdict_badge: str
    deal_summary: str
    simulated_recommendation: str


class SeedResponse(BaseModel):
    message: str
    products_created: int
    observations_created: int

