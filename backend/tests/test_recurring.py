"""Tests for deterministic recurring-transaction detection."""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from pathlib import Path

from app.services.recurring import (
    TxPoint,
    add_calendar_months,
    detect_recurring_series,
    expected_next_date,
)

FIXTURE = Path(__file__).resolve().parents[1] / "app/services/fixtures/recurring_transactions.json"


def _load_fixture() -> list[TxPoint]:
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return [
        TxPoint(
            account_id=int(row["account_id"]),
            merchant=str(row["merchant"]),
            date=date.fromisoformat(row["date"]),
            amount=Decimal(str(row["amount"])),
            category=str(row["category"]),
        )
        for row in raw
    ]


def test_fixed_monthly_subscription_detected() -> None:
    series = detect_recurring_series(_load_fixture())
    netflix = [
        s
        for s in series
        if s.normalized_merchant == "netflix" and s.account_id == 1
    ]
    assert len(netflix) == 1
    s = netflix[0]
    assert s.frequency == "monthly"
    assert s.amount_variability == "low"
    assert s.average_amount == Decimal("-15.99")
    assert s.transaction_count == 4
    assert s.expected_next_date == date(2026, 5, 3)
    assert s.confidence >= Decimal("0.55")


def test_variable_monthly_utility_detected() -> None:
    series = detect_recurring_series(_load_fixture())
    utility = [s for s in series if "power" in s.normalized_merchant]
    assert len(utility) == 1
    assert utility[0].frequency == "monthly"
    assert utility[0].amount_variability in {"medium", "high", "low"}
    # Relative range ~0.15 → medium
    assert utility[0].amount_variability == "medium"


def test_biweekly_payroll_detected() -> None:
    series = detect_recurring_series(_load_fixture())
    payroll = [s for s in series if "payroll" in s.normalized_merchant]
    assert len(payroll) == 1
    assert payroll[0].frequency == "biweekly"
    assert payroll[0].average_amount == Decimal("2200.00")
    assert payroll[0].expected_next_date == date(2026, 2, 28)


def test_one_off_merchant_not_detected() -> None:
    series = detect_recurring_series(_load_fixture())
    assert all(s.normalized_merchant != "costco" for s in series)


def test_irregular_cafe_not_high_confidence() -> None:
    series = detect_recurring_series(_load_fixture())
    cafe = [s for s in series if "cafe" in s.normalized_merchant]
    # Either not detected, or if somehow matched, confidence stays modest.
    assert cafe == [] or cafe[0].confidence < Decimal("0.55")


def test_february_month_length_monthly_series() -> None:
    series = detect_recurring_series(_load_fixture())
    edge = [s for s in series if "feb edge" in s.normalized_merchant]
    assert len(edge) == 1
    assert edge[0].frequency == "monthly"
    assert edge[0].expected_next_date == add_calendar_months(date(2026, 2, 28), 1)


def test_account_filter_via_input_subset() -> None:
    points = [p for p in _load_fixture() if p.account_id == 2]
    series = detect_recurring_series(points)
    assert len(series) == 1
    assert series[0].account_id == 2
    assert series[0].normalized_merchant == "netflix"


def test_expected_next_date_helpers() -> None:
    assert expected_next_date(date(2026, 1, 3), "weekly") == date(2026, 1, 10)
    assert expected_next_date(date(2026, 1, 3), "biweekly") == date(2026, 1, 17)
    assert expected_next_date(date(2026, 1, 31), "monthly") == date(2026, 2, 28)
    assert add_calendar_months(date(2024, 1, 31), 1) == date(2024, 2, 29)


def test_average_amount_is_decimal() -> None:
    series = detect_recurring_series(_load_fixture())
    netflix = next(s for s in series if s.normalized_merchant == "netflix" and s.account_id == 1)
    assert isinstance(netflix.average_amount, Decimal)
    assert isinstance(netflix.confidence, Decimal)


def test_descriptor_variants_do_not_merge_yet() -> None:
    """Documented limitation: NETFLIX.COM vs Netflix stay separate groups."""
    points = [
        TxPoint(1, "Netflix", date(2026, 1, 3), Decimal("-15.99"), "subscriptions"),
        TxPoint(1, "NETFLIX.COM", date(2026, 2, 3), Decimal("-15.99"), "subscriptions"),
        TxPoint(1, "Netflix", date(2026, 3, 3), Decimal("-15.99"), "subscriptions"),
        TxPoint(1, "Netflix", date(2026, 4, 3), Decimal("-15.99"), "subscriptions"),
    ]
    series = detect_recurring_series(points)
    # "netflix.com" has only 1 observation; "netflix" has 3 with a 2-month gap → may or may not pass.
    assert all(s.normalized_merchant != "netflix.com" for s in series)
