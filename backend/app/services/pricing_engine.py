import re
from app.utils.helpers import extract_prices

class PricingEngine:
    @staticmethod
    def apply_percentage(price: int, percent: float) -> int:
        return int(round(price * (1 + percent / 100)))

    @staticmethod
    def apply_fixed(price: int, amount: float) -> int:
        return int(round(price + amount))

    @staticmethod
    def apply_tiered(price: int, tiers: str) -> int:
        if not tiers:
            return price
        try:
            for line in tiers.strip().split("\n"):
                line = line.strip()
                if not line:
                    continue
                parts = re.split(r"[-:]\s*", line)
                if len(parts) >= 2:
                    upper_str = parts[0].strip().replace(",", "")
                    rule = parts[1].strip()
                    upper = int(upper_str)
                    if price <= upper:
                        if rule.startswith("+"):
                            if "%" in rule:
                                pct = float(rule.replace("%", "").replace("+", ""))
                                return PricingEngine.apply_percentage(price, pct)
                            else:
                                amt = float(rule.replace("+", ""))
                                return PricingEngine.apply_fixed(price, amt)
                        elif rule.startswith("x"):
                            mult = float(rule.replace("x", ""))
                            return int(round(price * mult))
            return price
        except Exception:
            return price

    @staticmethod
    def calculate_new_price(original_price: int, mode: str, value: float, tiers: str | None = None) -> int:
        if mode == "percentage":
            return PricingEngine.apply_percentage(original_price, value)
        elif mode == "fixed":
            return PricingEngine.apply_fixed(original_price, value)
        elif mode == "tiered":
            return PricingEngine.apply_tiered(original_price, tiers or "")
        return original_price

    @staticmethod
    def process_caption(caption: str, mode: str, value: float, tiers: str | None = None) -> tuple[str, int | None, int | None]:
        prices = extract_prices(caption)
        if not prices:
            return caption, None, None
        original_price = prices[0]
        new_price = PricingEngine.calculate_new_price(original_price, mode, value, tiers)
        return caption, original_price, new_price

pricing_engine = PricingEngine()
