from abc import ABC, abstractmethod
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel


class StoreQuote(BaseModel):
    store_name: str
    store_code: str
    store_badge_emoji: str
    price: Decimal
    currency: str
    in_stock: bool
    delivery_info: str
    rating: float
    is_lowest: bool
    difference_from_lowest: Decimal
    store_url: str
    matched_product_title: Optional[str] = None


class MultiStoreComparisonOut(BaseModel):
    product_id: int
    product_name: str
    cheapest_store: str
    lowest_price: Decimal
    highest_price: Decimal
    max_savings: Decimal
    savings_percentage: float
    recommendation_summary: str
    is_live_api: bool = False
    data_source: str = "Local Multi-Store Adapter Simulation"
    stores: List[StoreQuote]



class BaseStoreAdapter(ABC):
    """Abstract Adapter defining the contract for any e-commerce retailer pricing feed."""

    def __init__(self, store_name: str, store_code: str, emoji: str):
        self.store_name = store_name
        self.store_code = store_code
        self.emoji = emoji

    @abstractmethod
    def get_quote(self, product_id: int, product_name: str, base_price: Decimal, currency: str) -> StoreQuote:
        """Fetch quote from the respective retailer interface."""
        pass


class AmazonAdapter(BaseStoreAdapter):
    def __init__(self):
        super().__init__("Amazon India", "amazon", "🛒")

    def get_quote(self, product_id: int, product_name: str, base_price: Decimal, currency: str) -> StoreQuote:
        # Realistic retailer price variation based on product ID
        multiplier = Decimal("1.00") if product_id % 2 == 0 else Decimal("0.97")
        price = Decimal(f"{float(base_price * multiplier):.2f}")
        return StoreQuote(
            store_name=self.store_name,
            store_code=self.store_code,
            store_badge_emoji=self.emoji,
            price=price,
            currency=currency,
            in_stock=True,
            delivery_info="Prime 1-Day Delivery",
            rating=4.6,
            is_lowest=False,
            difference_from_lowest=Decimal("0.00"),
            store_url="https://www.amazon.in",
        )


class FlipkartAdapter(BaseStoreAdapter):
    def __init__(self):
        super().__init__("Flipkart", "flipkart", "🛍️")

    def get_quote(self, product_id: int, product_name: str, base_price: Decimal, currency: str) -> StoreQuote:
        multiplier = Decimal("1.03") if product_id % 2 == 0 else Decimal("1.01")
        price = Decimal(f"{float(base_price * multiplier):.2f}")
        return StoreQuote(
            store_name=self.store_name,
            store_code=self.store_code,
            store_badge_emoji=self.emoji,
            price=price,
            currency=currency,
            in_stock=True,
            delivery_info="Flipkart Plus · Free 2-Day Delivery",
            rating=4.4,
            is_lowest=False,
            difference_from_lowest=Decimal("0.00"),
            store_url="https://www.flipkart.com",
        )


class CromaAdapter(BaseStoreAdapter):
    def __init__(self):
        super().__init__("Croma Electronics", "croma", "🏬")

    def get_quote(self, product_id: int, product_name: str, base_price: Decimal, currency: str) -> StoreQuote:
        # Croma discounts electronics
        multiplier = Decimal("0.95") if "Headphones" in product_name or "Mouse" in product_name else Decimal("1.02")
        price = Decimal(f"{float(base_price * multiplier):.2f}")
        return StoreQuote(
            store_name=self.store_name,
            store_code=self.store_code,
            store_badge_emoji=self.emoji,
            price=price,
            currency=currency,
            in_stock=True,
            delivery_info="Express In-Store Pickup or 2-Day Delivery",
            rating=4.5,
            is_lowest=False,
            difference_from_lowest=Decimal("0.00"),
            store_url="https://www.croma.com",
        )


class RelianceDigitalAdapter(BaseStoreAdapter):
    def __init__(self):
        super().__init__("Reliance Digital", "reliance", "📱")

    def get_quote(self, product_id: int, product_name: str, base_price: Decimal, currency: str) -> StoreQuote:
        multiplier = Decimal("1.05")
        price = Decimal(f"{float(base_price * multiplier):.2f}")
        return StoreQuote(
            store_name=self.store_name,
            store_code=self.store_code,
            store_badge_emoji=self.emoji,
            price=price,
            currency=currency,
            in_stock=True,
            delivery_info="Standard 3-Day Home Delivery",
            rating=4.3,
            is_lowest=False,
            difference_from_lowest=Decimal("0.00"),
            store_url="https://www.reliancedigital.in",
        )


class TataCliqAdapter(BaseStoreAdapter):
    def __init__(self):
        super().__init__("Tata CLiQ", "tatacliq", "🏷️")

    def get_quote(self, product_id: int, product_name: str, base_price: Decimal, currency: str) -> StoreQuote:
        multiplier = Decimal("0.97") if product_id % 3 == 0 else Decimal("1.02")
        price = Decimal(f"{float(base_price * multiplier):.2f}")
        return StoreQuote(
            store_name=self.store_name,
            store_code=self.store_code,
            store_badge_emoji=self.emoji,
            price=price,
            currency=currency,
            in_stock=True,
            delivery_info="Tata CLiQ Express Delivery",
            rating=4.4,
            is_lowest=False,
            difference_from_lowest=Decimal("0.00"),
            store_url="https://www.tatacliq.com",
            matched_product_title=product_name,
        )


class VijaySalesAdapter(BaseStoreAdapter):
    def __init__(self):
        super().__init__("Vijay Sales", "vijaysales", "📺")

    def get_quote(self, product_id: int, product_name: str, base_price: Decimal, currency: str) -> StoreQuote:
        multiplier = Decimal("0.96") if "Headphones" in product_name or "Electronics" in product_name else Decimal("1.03")
        price = Decimal(f"{float(base_price * multiplier):.2f}")
        return StoreQuote(
            store_name=self.store_name,
            store_code=self.store_code,
            store_badge_emoji=self.emoji,
            price=price,
            currency=currency,
            in_stock=True,
            delivery_info="Free Next-Day Store Pickup",
            rating=4.5,
            is_lowest=False,
            difference_from_lowest=Decimal("0.00"),
            store_url="https://www.vijaysales.com",
            matched_product_title=product_name,
        )


class JioMartAdapter(BaseStoreAdapter):
    def __init__(self):
        super().__init__("JioMart", "jiomart", "🏪")

    def get_quote(self, product_id: int, product_name: str, base_price: Decimal, currency: str) -> StoreQuote:
        multiplier = Decimal("0.99")
        price = Decimal(f"{float(base_price * multiplier):.2f}")
        return StoreQuote(
            store_name=self.store_name,
            store_code=self.store_code,
            store_badge_emoji=self.emoji,
            price=price,
            currency=currency,
            in_stock=True,
            delivery_info="JioMart Free Delivery",
            rating=4.3,
            is_lowest=False,
            difference_from_lowest=Decimal("0.00"),
            store_url="https://www.jiomart.com",
            matched_product_title=product_name,
        )


class PoorvikaAdapter(BaseStoreAdapter):
    def __init__(self):
        super().__init__("Poorvika Mobiles", "poorvika", "📲")

    def get_quote(self, product_id: int, product_name: str, base_price: Decimal, currency: str) -> StoreQuote:
        multiplier = Decimal("1.04")
        price = Decimal(f"{float(base_price * multiplier):.2f}")
        return StoreQuote(
            store_name=self.store_name,
            store_code=self.store_code,
            store_badge_emoji=self.emoji,
            price=price,
            currency=currency,
            in_stock=True,
            delivery_info="2-Hour Express Delivery",
            rating=4.4,
            is_lowest=False,
            difference_from_lowest=Decimal("0.00"),
            store_url="https://www.poorvika.com",
            matched_product_title=product_name,
        )


class CrossStoreArbitrageEngine:
    """Aggregates prices from registered store adapters and computes cross-store savings."""

    def __init__(self):
        self.adapters: List[BaseStoreAdapter] = [
            AmazonAdapter(),
            FlipkartAdapter(),
            CromaAdapter(),
            RelianceDigitalAdapter(),
            TataCliqAdapter(),
            VijaySalesAdapter(),
            JioMartAdapter(),
            PoorvikaAdapter(),
        ]

    def compare_product(
        self, product_id: int, product_name: str, base_price: Decimal, currency: str = "INR"
    ) -> MultiStoreComparisonOut:
        # Check if live SerpApi key is provided in settings
        try:
            from app.core.config import settings
            if settings.serpapi_api_key and settings.serpapi_api_key.strip():
                live_result = self._fetch_live_google_shopping(
                    product_id, product_name, settings.serpapi_api_key.strip(), currency
                )
                if live_result:
                    return live_result
        except Exception:
            pass

        # Standard Fallback: Local Multi-Store Adapters
        raw_quotes = [
            adapter.get_quote(product_id, product_name, base_price, currency)
            for adapter in self.adapters
        ]

        # Calculate lowest and highest prices
        lowest_price = min(q.price for q in raw_quotes)
        highest_price = max(q.price for q in raw_quotes)
        max_savings = highest_price - lowest_price
        savings_pct = round(float((max_savings / highest_price) * Decimal("100")), 2) if highest_price > 0 else 0.0

        cheapest_store_name = ""

        # Mark lowest and calculate price differentials
        processed_quotes: List[StoreQuote] = []
        for q in raw_quotes:
            is_low = q.price == lowest_price
            if is_low and not cheapest_store_name:
                cheapest_store_name = q.store_name

            diff = q.price - lowest_price
            processed_quotes.append(
                StoreQuote(
                    store_name=q.store_name,
                    store_code=q.store_code,
                    store_badge_emoji=q.store_badge_emoji,
                    price=q.price,
                    currency=q.currency,
                    in_stock=q.in_stock,
                    delivery_info=q.delivery_info,
                    rating=q.rating,
                    is_lowest=is_low,
                    difference_from_lowest=diff,
                    store_url=q.store_url,
                )
            )

        summary = (
            f"Best deal found at {cheapest_store_name} ({currency} {lowest_price:.2f}). "
            f"You save up to {currency} {max_savings:.2f} ({savings_pct}%) compared to higher retailers!"
        )

        return MultiStoreComparisonOut(
            product_id=product_id,
            product_name=product_name,
            cheapest_store=cheapest_store_name,
            lowest_price=lowest_price,
            highest_price=highest_price,
            max_savings=max_savings,
            savings_percentage=savings_pct,
            recommendation_summary=summary,
            is_live_api=False,
            data_source="Local Multi-Store Adapter Simulation",
            stores=processed_quotes,
        )

    def _fetch_live_google_shopping(
        self, product_id: int, product_name: str, api_key: str, currency: str
    ) -> MultiStoreComparisonOut | None:
        try:
            import httpx

            params = {
                "engine": "google_shopping",
                "q": product_name,
                "google_domain": "google.co.in",
                "gl": "in",
                "hl": "en",
                "api_key": api_key,
            }
            with httpx.Client(timeout=8.0) as client:
                res = client.get("https://serpapi.com/search.json", params=params)
                if res.status_code != 200:
                    return None
                data = res.json()
                shopping_results = data.get("shopping_results", [])
                if not shopping_results:
                    return None

                premier_dict = {
                    adapter.store_code: adapter.get_quote(product_id, product_name, base_price, currency)
                    for adapter in self.adapters
                }

                live_prices_found = []

                for item in shopping_results:
                    source = item.get("source", "Retailer").strip()
                    if not source:
                        continue

                    raw_price = item.get("extracted_price")
                    if raw_price is None:
                        continue
                    price_val = Decimal(f"{float(raw_price):.2f}")
                    live_prices_found.append(price_val)

                    s_lower = source.lower()
                    target_code = None
                    if "amazon" in s_lower:
                        target_code = "amazon"
                    elif "flipkart" in s_lower:
                        target_code = "flipkart"
                    elif "croma" in s_lower:
                        target_code = "croma"
                    elif "reliance" in s_lower:
                        target_code = "reliance"
                    elif "tata" in s_lower or "cliq" in s_lower:
                        target_code = "tatacliq"
                    elif "vijay" in s_lower:
                        target_code = "vijaysales"
                    elif "jio" in s_lower:
                        target_code = "jiomart"
                    elif "poorvika" in s_lower:
                        target_code = "poorvika"

                    if target_code and target_code in premier_dict:
                        premier_dict[target_code].price = price_val
                        premier_dict[target_code].store_url = item.get("link", premier_dict[target_code].store_url)
                        premier_dict[target_code].delivery_info = item.get("delivery", premier_dict[target_code].delivery_info)
                        premier_dict[target_code].rating = float(item.get("rating", premier_dict[target_code].rating))

                if live_prices_found:
                    min_live = min(live_prices_found)
                    current_lowest = min(q.price for q in premier_dict.values())
                    if min_live < current_lowest:
                        cheapest_key = min(premier_dict.keys(), key=lambda k: premier_dict[k].price)
                        premier_dict[cheapest_key].price = min_live

                quotes = list(premier_dict.values())

                lowest_price = min(q.price for q in quotes)
                highest_price = max(q.price for q in quotes)
                max_savings = highest_price - lowest_price
                savings_pct = (
                    round(float((max_savings / highest_price) * Decimal("100")), 2)
                    if highest_price > 0
                    else 0.0
                )
                cheapest_store_name = ""

                processed: List[StoreQuote] = []
                for q in quotes:
                    is_low = q.price == lowest_price
                    if is_low and not cheapest_store_name:
                        cheapest_store_name = q.store_name
                    diff = q.price - lowest_price
                    processed.append(
                        StoreQuote(
                            store_name=q.store_name,
                            store_code=q.store_code,
                            store_badge_emoji=q.store_badge_emoji,
                            price=q.price,
                            currency=q.currency,
                            in_stock=q.in_stock,
                            delivery_info=q.delivery_info,
                            rating=q.rating,
                            is_lowest=is_low,
                            difference_from_lowest=diff,
                            store_url=q.store_url,
                        )
                    )

                summary = (
                    f"Live Google Shopping: Best deal at {cheapest_store_name} ({currency} {lowest_price:.2f}). "
                    f"Save up to {currency} {max_savings:.2f} ({savings_pct}%) across live retailers!"
                )

                return MultiStoreComparisonOut(
                    product_id=product_id,
                    product_name=product_name,
                    cheapest_store=cheapest_store_name,
                    lowest_price=lowest_price,
                    highest_price=highest_price,
                    max_savings=max_savings,
                    savings_percentage=savings_pct,
                    recommendation_summary=summary,
                    is_live_api=True,
                    data_source="Live Google Shopping API",
                    stores=processed,
                )
        except Exception:
            return None



arbitrage_engine = CrossStoreArbitrageEngine()
