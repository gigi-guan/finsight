"""Focused tests for pure transaction normalization helpers."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from app.services.transaction_normalize import (
    duplicate_key,
    normalize_category,
    normalize_merchant,
    parse_amount,
    parse_date,
)


def test_parse_date_iso_only() -> None:
    assert parse_date("2026-02-01") == date(2026, 2, 1)
    with pytest.raises(ValueError):
        parse_date("02/01/2026")


def test_parse_amount_decimal_safe() -> None:
    assert parse_amount("$1,234.50") == Decimal("1234.50")
    assert parse_amount("-15.99") == Decimal("-15.99")
    with pytest.raises(ValueError):
        parse_amount("1.999")
    with pytest.raises(ValueError):
        parse_amount("abc")


def test_normalize_merchant() -> None:
    assert normalize_merchant("  Netflix  ") == "netflix"
    assert normalize_merchant("NETFLIX.COM") == "netflix.com"
    assert normalize_merchant("Netflix") != normalize_merchant("NETFLIX.COM")


def test_normalize_category_policy() -> None:
    assert normalize_category(None) == "uncategorized"
    assert normalize_category("  ") == "uncategorized"
    assert normalize_category("Grocery") == "groceries"
    assert normalize_category("Made Up Label") == "other"
    assert normalize_category("INCOME") == "income"


def test_duplicate_key_uses_normalized_identity() -> None:
    a = duplicate_key(1, date(2026, 1, 1), "Netflix", Decimal("-15.99"), "Monthly")
    b = duplicate_key(1, date(2026, 1, 1), "  netflix ", Decimal("-15.99"), "monthly")
    c = duplicate_key(1, date(2026, 1, 1), "Spotify", Decimal("-15.99"), "Monthly")
    assert a == b
    assert a != c
