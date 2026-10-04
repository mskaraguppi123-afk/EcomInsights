"""ML package for EcomInsights: synthetic data loading and explainable price forecasting."""

from ecominsights_ml.data import load_sample_prices
from ecominsights_ml.pipeline import PriceTrendForecaster, analyze_price_series

__all__ = [
    "load_sample_prices",
    "PriceTrendForecaster",
    "analyze_price_series",
]
