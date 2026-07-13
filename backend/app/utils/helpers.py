import re
import hashlib
import json
from datetime import datetime, timezone

PRICE_PATTERNS = [
    re.compile(r"[\u20B9Rs.\s]*(\d[\d,]*)\s*(?:/-|\.00)?", re.IGNORECASE),
    re.compile(r"(\d[\d,]*)\s*(?:rupees?|rs\.?)", re.IGNORECASE),
    re.compile(r"price[:\s]*[\u20B9Rs.\s]*(\d[\d,]*)", re.IGNORECASE),
    re.compile(r"₹(\d[\d,]*)"),
]

def extract_prices(text: str) -> list[int]:
    prices = set()
    for pattern in PRICE_PATTERNS:
        for match in pattern.finditer(text):
            cleaned = match.group(1).replace(",", "")
            try:
                prices.add(int(cleaned))
            except ValueError:
                pass
    return sorted(prices)

def replace_price(text: str, old_price: int, new_price: int) -> str:
    for pattern in PRICE_PATTERNS:
        def replacer(m, op=old_price, np=new_price):
            try:
                if int(m.group(1).replace(",", "")) == op:
                    prefix = m.group(0)[:m.start(1) - m.start(0)]
                    return f"{prefix}{np:,}"
            except ValueError:
                pass
            return m.group(0)
        text = pattern.sub(replacer, text)
    return text

def compute_product_hash(caption: str, media_count: int, source_group_id: str) -> str:
    raw = f"{caption.strip()}|{media_count}|{source_group_id}"
    return hashlib.sha256(raw.encode()).hexdigest()

def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()

def serialize_row(row) -> dict:
    if row is None:
        return None
    return dict(row)
