"""Account ORM model — maps to the `accounts` PostgreSQL table."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.transaction import Transaction


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    account_type: Mapped[str] = mapped_column(String(50), nullable=False)
    institution: Mapped[str] = mapped_column(String(255), nullable=False)
    # Manually reported snapshot balance at create/edit time — NOT a live ledger
    # derived from transactions. Numeric/Decimal — never float for money.
    current_balance: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    transactions: Mapped[list[Transaction]] = relationship(
        back_populates="account",
    )
