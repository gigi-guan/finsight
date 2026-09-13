"""Pure transaction normalization helpers (no DB / FastAPI / ORM).

Shared by CSV import, manual create, and (later) ML feature prep.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation

# Canonical taxonomy for analytics + future categorization ML.
CANONICAL_CATEGORIES: frozenset[str] = frozenset(
    {
        "income",
        "housing",
        "groceries",
        "dining",
        "transportation",
        "travel",
        "shopping",
        "entertainment",
        "utilities",
        "healthcare",
        "subscriptions",
        "other",
        "uncategorized",
    }
)

CATEGORY_SOURCES: frozenset[str] = frozenset(
    {"user", "csv", "rules", "model", "unknown"}
)

# Common aliases → canonical (casefold keys).
_CATEGORY_ALIASES: dict[str, str] = {
    "grocery": "groceries",
    "groceries": "groceries",
    "food": "dining",
    "dining": "dining",
    "restaurant": "dining",
    "restaurants": "dining",
    "transport": "transportation",
    "transportation": "transportation",
    "transit": "transportation",
    "gas": "transportation",
    "fuel": "transportation",
    "health": "healthcare",
    "healthcare": "healthcare",
    "medical": "healthcare",
    "rent": "housing",
    "mortgage": "housing",
    "housing": "housing",
    "util": "utilities",
    "utility": "utilities",
    "utilities": "utilities",
    "sub": "subscriptions",
    "subscription": "subscriptions",
    "subscriptions": "subscriptions",
    "income": "income",
    "payroll": "income",
    "salary": "income",
    "shopping": "shopping",
    "entertainment": "entertainment",
    "travel": "travel",
    "other": "other",
    "uncategorized": "uncategorized",
}

DuplicateKey = tuple[int, date, str, Decimal, str]


def parse_date(raw: str) -> date:
    """Accept ISO calendar dates only (YYYY-MM-DD)."""
    try:
        return date.fromisoformat(raw.strip())
    except ValueError as exc:
        raise ValueError("Invalid date; use YYYY-MM-DD") from exc


def parse_amount(raw: str) -> Decimal:
    """Parse money with Decimal. Allows optional leading $ and thousands commas."""
    cleaned = raw.strip().replace("$", "").replace(",", "")
    if not cleaned:
        raise ValueError("Invalid decimal value")
    try:
        amount = Decimal(cleaned)
    except InvalidOperation as exc:
        raise ValueError("Invalid decimal value") from exc

    exponent = amount.as_tuple().exponent
    if isinstance(exponent, int) and exponent < -2:
        raise ValueError("Amount must have at most 2 decimal places")

    amount = amount.quantize(Decimal("0.01"))
    if abs(amount) >= Decimal("1000000000000"):
        raise ValueError("Amount out of supported range")
    return amount


def normalize_merchant(raw: str) -> str:
    """Lightweight merchant key for dedupe / future ML features (does not replace storage)."""
    return " ".join(raw.strip().split()).casefold()


def normalize_category(raw: str | None) -> str:
    """Map a category string to the canonical taxonomy.

    Policy:
    - blank/missing → uncategorized
    - known canonical / alias (case/whitespace insensitive) → canonical value
    - unsupported → other (closed taxonomy; do not invent new labels)
    """
    if raw is None:
        return "uncategorized"
    cleaned = " ".join(str(raw).strip().split())
    if not cleaned:
        return "uncategorized"

    key = cleaned.casefold()
    if key in _CATEGORY_ALIASES:
        return _CATEGORY_ALIASES[key]
    if key in CANONICAL_CATEGORIES:
        return key
    return "other"


def duplicate_key(
    account_id: int,
    tx_date: date,
    merchant: str,
    amount: Decimal,
    description: str,
) -> DuplicateKey:
    """Heuristic identity for near-duplicate detection within an account."""
    return (
        account_id,
        tx_date,
        normalize_merchant(merchant),
        amount,
        description.strip().casefold(),
    )
