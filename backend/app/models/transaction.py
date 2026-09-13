"""Transaction ORM model — maps to the `transactions` PostgreSQL table."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.account import Account


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        CheckConstraint(
            "category_confidence IS NULL OR "
            "(category_confidence >= 0 AND category_confidence <= 1)",
            name="ck_transactions_category_confidence_range",
        ),
        Index("ix_transactions_account_id_date", "account_id", "date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    # FK column enforces referential integrity in PostgreSQL.
    # ondelete="RESTRICT" blocks deleting an account that still has transactions.
    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    merchant: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    # Signed amount: income positive, expense negative. Never Float.
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    # Provenance: user | csv | rules | model | unknown
    category_source: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="unknown",
    )
    # Only meaningful when category_source == "model"; otherwise null.
    category_confidence: Mapped[Decimal | None] = mapped_column(
        Numeric(4, 3),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # ORM relationship — Python-side navigation, not an extra DB column.
    account: Mapped[Account] = relationship(back_populates="transactions")
