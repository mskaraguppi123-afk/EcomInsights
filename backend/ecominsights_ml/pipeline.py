"""Price trend forecasting and analytical recommendation pipeline.

Designed for college project demonstrations and explainable time-series baselines:
- Uses a weighted blend of Exponential Moving Average (EMA) and Linear Trend Extrapolation.
- Generates actionable decision-support metrics (Trend Direction, Momentum, Buy/Wait Advice).
"""

from decimal import Decimal
from typing import Any, Sequence


class PriceTrendForecaster:
    """Explainable time-series baseline forecaster for sparse e-commerce price observations."""

    def __init__(self, ema_alpha: float = 0.5, linear_weight: float = 0.4):
        self.ema_alpha = ema_alpha
        self.linear_weight = linear_weight
        self.ema_weight = 1.0 - linear_weight

    def forecast_and_analyze(
        self,
        prices: Sequence[Decimal | float | int],
    ) -> dict[str, Any]:
        """Compute trend momentum, estimate the next price checkpoint, and provide buy advice."""
        n = len(prices)

        if n == 0:
            return {
                "predicted_next_price": Decimal("0.00"),
                "trend_direction": "UNKNOWN",
                "change_percentage": 0.0,
                "recommendation": "NEUTRAL",
                "recommendation_reason": "No price observations available yet.",
                "lowest_price": Decimal("0.00"),
                "highest_price": Decimal("0.00"),
                "average_price": Decimal("0.00"),
                "observation_count": 0,
            }

        numeric_prices = [float(p) for p in prices]
        current_price = numeric_prices[-1]
        first_price = numeric_prices[0]
        min_price = min(numeric_prices)
        max_price = max(numeric_prices)
        avg_price = sum(numeric_prices) / n

        if n == 1:
            dec_price = Decimal(f"{current_price:.2f}")
            return {
                "predicted_next_price": dec_price,
                "trend_direction": "STABLE",
                "change_percentage": 0.0,
                "recommendation": "NEUTRAL",
                "recommendation_reason": "Only 1 historical observation available.",
                "lowest_price": dec_price,
                "highest_price": dec_price,
                "average_price": dec_price,
                "observation_count": 1,
            }

        # 1. Trend Direction & Recent Momentum
        prev_price = numeric_prices[-2]
        recent_change_pct = ((current_price - prev_price) / prev_price) * 100.0 if prev_price > 0 else 0.0
        overall_change_pct = ((current_price - first_price) / first_price) * 100.0 if first_price > 0 else 0.0

        if recent_change_pct > 0.5:
            trend_direction = "UP"
        elif recent_change_pct < -0.5:
            trend_direction = "DOWN"
        else:
            trend_direction = "STABLE"

        # 2. Linear Trend Extrapolation (Simple OLS on time steps x = 0..n-1)
        x_indices = list(range(n))
        x_mean = (n - 1) / 2.0
        y_mean = avg_price

        denom = sum((x - x_mean) ** 2 for x in x_indices)
        if denom > 0:
            numer = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_indices, numeric_prices))
            slope = numer / denom
            intercept = y_mean - slope * x_mean
            linear_next = slope * n + intercept
        else:
            linear_next = current_price

        # 3. Exponential Moving Average (EMA)
        ema = numeric_prices[0]
        for val in numeric_prices[1:]:
            ema = self.ema_alpha * val + (1.0 - self.ema_alpha) * ema

        # 4. Ensembled Next Price Estimate
        blended_next = (self.linear_weight * linear_next) + (self.ema_weight * ema)
        predicted_next_price = max(0.01, round(blended_next, 2))

        # 5. Smart Buy/Wait Recommendation (Position in Historical Range)
        price_spread = max_price - min_price
        if price_spread > 0:
            range_ratio = (current_price - min_price) / price_spread
            if range_ratio <= 0.35:
                recommendation = "BUY_NOW"
                reason = f"Current price (Rs. {current_price:.2f}) is close to historical low (Rs. {min_price:.2f}). Good time to buy!"
            elif range_ratio >= 0.75 and trend_direction != "DOWN":
                recommendation = "WAIT"
                reason = f"Current price (Rs. {current_price:.2f}) is near historical peak (Rs. {max_price:.2f}). Consider waiting for a price drop."
            else:
                recommendation = "NEUTRAL"
                reason = f"Current price (Rs. {current_price:.2f}) is within standard historical range."
        else:
            recommendation = "NEUTRAL"
            reason = "Price has remained steady across observations."

        return {
            "predicted_next_price": Decimal(f"{predicted_next_price:.2f}"),
            "trend_direction": trend_direction,
            "change_percentage": round(recent_change_pct, 2),
            "recommendation": recommendation,
            "recommendation_reason": reason,
            "lowest_price": Decimal(f"{min_price:.2f}"),
            "highest_price": Decimal(f"{max_price:.2f}"),
            "average_price": Decimal(f"{avg_price:.2f}"),
            "observation_count": n,
        }


def analyze_price_series(prices: Sequence[Decimal | float | int]) -> dict[str, Any]:
    """Convenience helper to analyze a price sequence."""
    forecaster = PriceTrendForecaster()
    return forecaster.forecast_and_analyze(prices)
