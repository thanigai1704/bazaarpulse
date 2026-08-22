"""Indian-rupee utilities: parsing and formatting.

Indian digit grouping uses lakhs/crores, e.g. 1,45,999 (not 145,999).
"""

import re

_INDIAN_GROUPING = re.compile(r"(\d)(?=(\d{2})+\d{1,3}(?!\d))")


def format_inr(amount: int | float) -> str:
    """Format an amount in Indian grouping with a ₹ symbol.

    >>> format_inr(145999)
    '₹1,45,999'
    >>> format_inr(249999)
    '₹2,49,999'
    >>> format_inr(18999)
    '₹18,999'
    """
    value = int(round(float(amount)))
    if value < 0:
        return "-" + format_inr(-value)
    if value < 1000:
        return f"₹{value}"
    grouped = _INDIAN_GROUPING.sub(r"\1,", str(value))
    return f"₹{grouped}"


def parse_price(raw: str) -> int | None:
    """Parse messy Indian price strings like '₹1,45,999' or '1,45,999'.

    Handles: rupee symbol, commas (lakh/crore grouping), decimals,
    'Rs', whitespace and surrounding noise.
    """
    if raw is None:
        return None
    cleaned = re.sub(r"[^\d.,-]", "", str(raw))
    cleaned = re.sub(r",(?=\d{3})", "", cleaned)  # western grouping 145,999
    cleaned = cleaned.replace(",", "")  # indian grouping 1,45,999
    if not cleaned or cleaned in ("-", "."):
        return None
    try:
        return int(float(cleaned))
    except ValueError:
        return None


def parse_discount_pct(raw: str) -> float | None:
    """Extract '38% off' → 38.0."""
    if raw is None:
        return None
    match = re.search(r"(\d+(?:\.\d+)?)\s*%", str(raw))
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None
