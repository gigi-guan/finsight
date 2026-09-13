"""Pydantic schemas for the Account API."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class AccountCreate(BaseModel):
    """Payload for creating an account (client cannot set id / created_at)."""

    name: str = Field(min_length=1, max_length=255)
    account_type: str = Field(min_length=1, max_length=50)
    institution: str = Field(min_length=1, max_length=255)
    current_balance: Decimal = Field(max_digits=14, decimal_places=2)


class AccountRead(BaseModel):
    """Account as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    account_type: str
    institution: str
    current_balance: Decimal
    created_at: datetime
