"""Schemas for recurring-transaction analytics."""

from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

Frequency = Literal["weekly", "biweekly", "monthly"]
AmountVariability = Literal["low", "medium", "high"]


class RecurringSeries(BaseModel):
    """One detected recurring payment/income stream (computed, not stored)."""

    merchant: str
    normalized_merchant: str
    account_id: int
    category: str
    frequency: Frequency
    transaction_count: int = Field(ge=3)
    average_amount: Decimal
    amount_variability: AmountVariability
    last_date: date
    expected_next_date: date
    # Heuristic 0–1 score — NOT a calibrated ML probability.
    confidence: Decimal = Field(ge=0, le=1)
