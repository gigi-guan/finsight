"""Shared TestClient + in-memory SQLite helpers for API tests."""

from __future__ import annotations

from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.account import Account


def client_with_db():
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


def cleanup_client(client: TestClient, db: Session, engine) -> None:
    db.close()
    app.dependency_overrides.clear()
    engine.dispose()


def create_account(
    db: Session,
    *,
    name: str = "Checking",
    balance: str = "100.00",
) -> Account:
    account = Account(
        name=name,
        account_type="checking",
        institution="Test Bank",
        current_balance=Decimal(balance),
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account
