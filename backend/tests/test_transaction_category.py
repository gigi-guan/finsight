"""Tests for transaction category review/correction."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.account import Account
from app.models.transaction import Transaction


def _client_with_db():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    db = TestingSessionLocal()
    return client, db, engine


def test_patch_category_sets_user_source_and_clears_confidence() -> None:
    client, db, engine = _client_with_db()
    try:
        account = Account(
            name="Checking",
            account_type="checking",
            institution="Test Bank",
            current_balance=Decimal("100.00"),
        )
        db.add(account)
        db.commit()
        db.refresh(account)

        tx = Transaction(
            account_id=account.id,
            date=date(2026, 9, 1),
            merchant="CSV Grocer",
            description="Milk",
            amount=Decimal("-6.50"),
            category="uncategorized",
            category_source="csv",
            category_confidence=Decimal("0.91"),
        )
        db.add(tx)
        db.commit()
        db.refresh(tx)

        response = client.patch(
            f"/transactions/{tx.id}/category",
            json={"category": " Groceries "},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["category"] == "groceries"
        assert body["category_source"] == "user"
        assert body["category_confidence"] is None

        db.expire_all()
        refreshed = db.get(Transaction, tx.id)
        assert refreshed is not None
        assert refreshed.category == "groceries"
        assert refreshed.category_source == "user"
        assert refreshed.category_confidence is None
    finally:
        app.dependency_overrides.clear()
        db.close()
        engine.dispose()


def test_patch_category_not_found() -> None:
    client, db, engine = _client_with_db()
    try:
        response = client.patch(
            "/transactions/999999/category",
            json={"category": "shopping"},
        )
        assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()
        db.close()
        engine.dispose()


def test_patch_unsupported_category_maps_to_other() -> None:
    client, db, engine = _client_with_db()
    try:
        account = Account(
            name="Checking",
            account_type="checking",
            institution="Test Bank",
            current_balance=Decimal("100.00"),
        )
        db.add(account)
        db.commit()
        db.refresh(account)
        tx = Transaction(
            account_id=account.id,
            date=date(2026, 9, 1),
            merchant="X",
            description="Y",
            amount=Decimal("-1.00"),
            category="shopping",
            category_source="unknown",
            category_confidence=None,
        )
        db.add(tx)
        db.commit()
        db.refresh(tx)

        response = client.patch(
            f"/transactions/{tx.id}/category",
            json={"category": "Totally Invented"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["category"] == "other"
        assert body["category_source"] == "user"
    finally:
        app.dependency_overrides.clear()
        db.close()
        engine.dispose()
