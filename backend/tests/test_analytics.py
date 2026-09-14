"""Analytics summary tests — month bounds, MoM wraparound, null % , filters."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.models.transaction import Transaction
from app.services.analytics import (
    month_bounds,
    parse_month,
    previous_month,
)
from tests.conftest import cleanup_client, client_with_db, create_account


def test_month_bounds() -> None:
    assert month_bounds(2026, 9) == (date(2026, 9, 1), date(2026, 10, 1))
    assert month_bounds(2026, 12) == (date(2026, 12, 1), date(2027, 1, 1))
    assert month_bounds(2026, 2) == (date(2026, 2, 1), date(2026, 3, 1))


def test_previous_month_wraparound() -> None:
    assert previous_month(2026, 1) == (2025, 12)
    assert previous_month(2026, 12) == (2026, 11)
    assert previous_month(2026, 3) == (2026, 2)


def test_parse_month_rejects_bad_format() -> None:
    with pytest.raises(HTTPException) as exc:
        parse_month("2026-9")
    assert exc.value.status_code == 400


def _add_tx(
    db,
    account_id: int,
    *,
    tx_date: date,
    merchant: str,
    amount: str,
    category: str = "other",
) -> None:
    db.add(
        Transaction(
            account_id=account_id,
            date=tx_date,
            merchant=merchant,
            description="",
            amount=Decimal(amount),
            category=category,
            category_source="user",
            category_confidence=None,
        )
    )


def test_income_spending_net_and_jan_dec_wrap() -> None:
    client, db, engine = client_with_db()
    try:
        account = create_account(db)
        # December 2025 spending
        _add_tx(
            db,
            account.id,
            tx_date=date(2025, 12, 15),
            merchant="Rent",
            amount="-1000.00",
            category="housing",
        )
        # January 2026 income + spending
        _add_tx(
            db,
            account.id,
            tx_date=date(2026, 1, 5),
            merchant="Payroll",
            amount="2000.00",
            category="income",
        )
        _add_tx(
            db,
            account.id,
            tx_date=date(2026, 1, 10),
            merchant="Grocer",
            amount="-50.00",
            category="groceries",
        )
        # Outside January — ignored for Jan summary
        _add_tx(
            db,
            account.id,
            tx_date=date(2026, 2, 1),
            merchant="Later",
            amount="-9.00",
            category="other",
        )
        db.commit()

        response = client.get("/analytics/summary", params={"month": "2026-01"})
        assert response.status_code == 200
        body = response.json()
        assert body["month"] == "2026-01"
        assert body["total_income"] == "2000.00"
        assert body["total_spending"] == "50.00"
        assert body["net_cash_flow"] == "1950.00"
        assert body["transaction_count"] == 2
        assert body["previous_month"]["total_spending"] == "1000.00"
        assert body["previous_month"]["spending_change_amount"] == "-950.00"
        assert body["previous_month"]["spending_change_percent"] == "-95.00"
    finally:
        cleanup_client(client, db, engine)


def test_zero_previous_spending_null_percent() -> None:
    client, db, engine = client_with_db()
    try:
        account = create_account(db)
        _add_tx(
            db,
            account.id,
            tx_date=date(2026, 3, 2),
            merchant="Store",
            amount="-40.00",
            category="shopping",
        )
        db.commit()

        response = client.get("/analytics/summary", params={"month": "2026-03"})
        assert response.status_code == 200
        body = response.json()
        assert body["total_spending"] == "40.00"
        assert body["previous_month"]["total_spending"] == "0.00"
        assert body["previous_month"]["spending_change_percent"] is None
    finally:
        cleanup_client(client, db, engine)


def test_account_filtering() -> None:
    client, db, engine = client_with_db()
    try:
        a1 = create_account(db, name="A1")
        a2 = create_account(db, name="A2")
        _add_tx(
            db,
            a1.id,
            tx_date=date(2026, 4, 1),
            merchant="Only A1",
            amount="-25.00",
        )
        _add_tx(
            db,
            a2.id,
            tx_date=date(2026, 4, 1),
            merchant="Only A2",
            amount="-75.00",
        )
        db.commit()

        all_resp = client.get("/analytics/summary", params={"month": "2026-04"})
        assert all_resp.json()["total_spending"] == "100.00"

        a1_resp = client.get(
            "/analytics/summary",
            params={"month": "2026-04", "account_id": a1.id},
        )
        assert a1_resp.status_code == 200
        assert a1_resp.json()["total_spending"] == "25.00"
        assert a1_resp.json()["top_merchants"][0]["merchant"] == "Only A1"
    finally:
        cleanup_client(client, db, engine)
