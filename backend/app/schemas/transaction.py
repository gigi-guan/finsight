"""Pydantic schemas for the Transaction API."""

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

CategorySource = Literal["user", "csv", "rules", "model", "unknown"]


class TransactionCreate(BaseModel):
    """Payload for creating a transaction."""

    account_id: int = Field(gt=0)
    date: date
    merchant: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1, max_length=500)
    # Signed decimal: income positive, expense negative.
    amount: Decimal = Field(max_digits=14, decimal_places=2)
    # Optional; blank → uncategorized via normalize_category. Server sets source=user.
    category: str = Field(default="", max_length=100)


class TransactionCategoryUpdate(BaseModel):
    """Payload for PATCH /transactions/{id}/category.

    Clients send only the category string. The server owns provenance fields:
    category_source becomes \"user\" and category_confidence is cleared.
    """

    category: str = Field(max_length=100)


class TransactionRead(BaseModel):
    """Transaction as returned by the API (includes account_name for display)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    account_id: int
    account_name: str
    date: date
    merchant: str
    description: str
    amount: Decimal
    category: str
    category_source: CategorySource
    category_confidence: Decimal | None = None
    created_at: datetime

    @field_validator("category_confidence")
    @classmethod
    def confidence_in_unit_interval(cls, value: Decimal | None) -> Decimal | None:
        if value is None:
            return value
        if value < 0 or value > 1:
            raise ValueError("category_confidence must be between 0 and 1 inclusive")
        return value


class TransactionImportError(BaseModel):
    """One rejected CSV row.

    `row` is the CSV parser physical 1-based line number (`csv.DictReader.line_num`),
    not a logical data-row index. Blank lines still advance the physical line.
    """

    row: int
    field: str | None = None
    message: str


class TransactionImportResult(BaseModel):
    """Summary returned by POST /transactions/import."""

    total_rows: int
    imported: int
    rejected: int
    duplicates: int
    errors: list[TransactionImportError]
