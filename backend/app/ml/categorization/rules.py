"""Simple deterministic rule baseline for transaction categorization."""

from __future__ import annotations

from dataclasses import dataclass

from app.services.transaction_normalize import normalize_merchant

# Intentionally small: obvious merchant/keyword → category mappings.
# Order matters: first match wins.
_RULES: list[tuple[tuple[str, ...], str]] = [
    (("whole foods", "safeway", "trader joe", "kroger", "aldi", "publix", "grocery"), "groceries"),
    (("uber eats", "doordash", "chipotle", "starbucks", "mcdonald", "olive garden", "restaurant", "cafe"), "dining"),
    (("uber", "lyft", "shell", "chevron", "exxon", "parking", "transit", "toll"), "transportation"),
    (("united", "delta", "southwest", "american airlines", "marriott", "hilton", "hyatt", "airbnb", "expedia", "airline", "hotel"), "travel"),
    (("netflix", "spotify", "disney+", "hulu", "icloud", "adobe", "subscription", "github", "dropbox", "youtube premium"), "subscriptions"),
    (("amc", "steam", "ticketmaster", "xbox", "playstation", "concert", "movie", "zoo", "museum"), "entertainment"),
    (("amazon", "target", "walmart", "best buy", "nike", "ikea", "home depot", "macy", "ebay", "apple store"), "shopping"),
    (("pg&e", "comcast", "at&t", "verizon", "t-mobile", "spectrum", "utility", "electric", "internet bill", "water"), "utilities"),
    (("cvs", "walgreens", "pharmacy", "hospital", "dental", "kaiser", "urgent care", "labcorp", "rite aid"), "healthcare"),
    (("rent", "mortgage", "hoa", "landlord", "apartment", "escrow", "condo"), "housing"),
    (("payroll", "paycheck", "salary", "direct deposit", "dividend", "tax refund", "bonus", "invoice payment"), "income"),
]


@dataclass(frozen=True)
class RulePrediction:
    category: str
    matched_rule: str | None


def predict_category(merchant: str, description: str) -> RulePrediction:
    """Return a category from simple substring rules, else uncategorized."""
    text = f"{normalize_merchant(merchant)} {description.strip().casefold()}"
    for patterns, category in _RULES:
        for pattern in patterns:
            if pattern in text:
                return RulePrediction(category=category, matched_rule=pattern)
    return RulePrediction(category="uncategorized", matched_rule=None)


def predict_many(merchants: list[str], descriptions: list[str]) -> list[str]:
    return [
        predict_category(merchant, description).category
        for merchant, description in zip(merchants, descriptions, strict=True)
    ]
