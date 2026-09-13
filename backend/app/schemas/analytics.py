"""Pydantic schemas for analytics endpoints."""

from decimal import Decimal

from pydantic import BaseModel, Field


class PreviousMonthComparison(BaseModel):
    total_spending: Decimal
    spending_change_amount: Decimal
    # null when previous spending is 0 and current spending is not (undefined %).
    spending_change_percent: Decimal | None = None


class CategorySpending(BaseModel):
    category: str
    amount: Decimal
    percent_of_spending: Decimal


class MerchantSpending(BaseModel):
    merchant: str
    amount: Decimal
    transaction_count: int = Field(ge=0)


class AnalyticsSummary(BaseModel):
    month: str
    total_income: Decimal
    total_spending: Decimal
    net_cash_flow: Decimal
    transaction_count: int = Field(ge=0)
    previous_month: PreviousMonthComparison
    spending_by_category: list[CategorySpending]
    top_merchants: list[MerchantSpending]
