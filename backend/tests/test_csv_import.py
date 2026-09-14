"""CSV import endpoint tests — partial success, duplicates, physical line numbers."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from io import BytesIO

from app.models.transaction import Transaction
from tests.conftest import cleanup_client, client_with_db, create_account


def _import(client, account_id: int, content: bytes | str, filename: str = "rows.csv"):
    if isinstance(content, str):
        content = content.encode("utf-8")
    return client.post(
        "/transactions/import",
        data={"account_id": str(account_id)},
        files={"file": (filename, BytesIO(content), "text/csv")},
    )


def test_valid_import() -> None:
    client, db, engine = client_with_db()
    try:
        account = create_account(db)
        csv_text = (
            "date,merchant,amount,description,category\n"
            "2026-01-02,Netflix,-15.99,Monthly,subscriptions\n"
            "2026-01-03,Payroll,2200.00,Pay,income\n"
        )
        response = _import(client, account.id, csv_text)
        assert response.status_code == 200
        body = response.json()
        assert body["total_rows"] == 2
        assert body["imported"] == 2
        assert body["rejected"] == 0
        assert body["duplicates"] == 0
        assert body["errors"] == []

        rows = db.query(Transaction).filter_by(account_id=account.id).all()
        assert len(rows) == 2
        assert all(r.category_source == "csv" for r in rows)
        assert {r.merchant for r in rows} == {"Netflix", "Payroll"}
    finally:
        cleanup_client(client, db, engine)


def test_partial_success() -> None:
    client, db, engine = client_with_db()
    try:
        account = create_account(db)
        csv_text = (
            "date,merchant,amount\n"
            "2026-01-02,Good Store,-10.00\n"
            "not-a-date,Bad Date,-5.00\n"
            "2026-01-04,Also Good,-3.50\n"
        )
        response = _import(client, account.id, csv_text)
        assert response.status_code == 200
        body = response.json()
        assert body["total_rows"] == 3
        assert body["imported"] == 2
        assert body["rejected"] == 1
        assert body["duplicates"] == 0
        assert len(body["errors"]) == 1
        assert body["errors"][0]["field"] == "date"
        assert body["errors"][0]["row"] == 3

        rows = db.query(Transaction).filter_by(account_id=account.id).all()
        assert len(rows) == 2
        assert {r.merchant for r in rows} == {"Good Store", "Also Good"}
    finally:
        cleanup_client(client, db, engine)


def test_duplicate_handling() -> None:
    client, db, engine = client_with_db()
    try:
        account = create_account(db)
        db.add(
            Transaction(
                account_id=account.id,
                date=date(2026, 1, 2),
                merchant="Netflix",
                description="Monthly",
                amount=Decimal("-15.99"),
                category="subscriptions",
                category_source="user",
                category_confidence=None,
            )
        )
        db.commit()

        csv_text = (
            "date,merchant,amount,description\n"
            "2026-01-02,Netflix,-15.99,Monthly\n"
            "2026-01-02,Netflix,-15.99,Monthly\n"
            "2026-01-05,Spotify,-10.99,Monthly\n"
        )
        response = _import(client, account.id, csv_text)
        assert response.status_code == 200
        body = response.json()
        assert body["imported"] == 1
        assert body["duplicates"] == 2
        assert body["rejected"] == 0
        assert len(body["errors"]) == 2
        assert all("Duplicate" in e["message"] for e in body["errors"])

        rows = db.query(Transaction).filter_by(account_id=account.id).all()
        assert len(rows) == 2
        assert {r.merchant for r in rows} == {"Netflix", "Spotify"}
    finally:
        cleanup_client(client, db, engine)


def test_malformed_headers() -> None:
    client, db, engine = client_with_db()
    try:
        account = create_account(db)
        response = _import(client, account.id, "foo,bar\n1,2\n")
        assert response.status_code == 400
        assert "missing required columns" in response.json()["detail"].lower()
    finally:
        cleanup_client(client, db, engine)


def test_invalid_encoding() -> None:
    client, db, engine = client_with_db()
    try:
        account = create_account(db)
        # Latin-1 bytes that are not valid UTF-8.
        content = b"date,merchant,amount\n2026-01-02,Caf\xe9,-5.00\n"
        response = _import(client, account.id, content)
        assert response.status_code == 400
        assert "utf-8" in response.json()["detail"].lower()
    finally:
        cleanup_client(client, db, engine)


def test_file_too_large() -> None:
    client, db, engine = client_with_db()
    try:
        account = create_account(db)
        huge = b"date,merchant,amount\n" + (b"2026-01-02,X,-1.00\n" * 200000)
        assert len(huge) > 2 * 1024 * 1024
        response = _import(client, account.id, huge)
        assert response.status_code == 400
        assert "maximum size" in response.json()["detail"].lower()
    finally:
        cleanup_client(client, db, engine)


def test_physical_row_numbers_after_blank_lines() -> None:
    client, db, engine = client_with_db()
    try:
        account = create_account(db)
        # Line 1 header, 2 blank, 3 valid, 4 blank, 5 invalid amount
        csv_text = (
            "date,merchant,amount\n"
            "\n"
            "2026-01-02,Ok,-10.00\n"
            "\n"
            "2026-01-03,Bad,not-money\n"
        )
        response = _import(client, account.id, csv_text)
        assert response.status_code == 200
        body = response.json()
        assert body["imported"] == 1
        assert body["rejected"] == 1
        assert body["errors"][0]["row"] == 5
        assert body["errors"][0]["field"] == "amount"
    finally:
        cleanup_client(client, db, engine)
