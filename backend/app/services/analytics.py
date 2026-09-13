"""Analytics service — month-bounded aggregates computed in PostgreSQL."""

from __future__ import annotations

from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from fastapi import HTTPException, status
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models.transaction import Transaction
from app.schemas.analytics import (
    AnalyticsSummary,
    CategorySpending,
    MerchantSpending,
    PreviousMonthComparison,
)
from app.services.transaction import require_account

ZERO = Decimal("0.00")
CENT = Decimal("0.01")
TOP_MERCHANTS_LIMIT = 5


def _quantize_money(value: Decimal | None) -> Decimal:
    if value is None:
        return ZERO
    return Decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)


def _quantize_percent(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def parse_month(month: str | None) -> tuple[int, int, str]:
    """Parse YYYY-MM or default to the current calendar month."""
    if month is None or month.strip() == "":
        today = date.today()
        return today.year, today.month, f"{today.year:04d}-{today.month:02d}"

    raw = month.strip()
    try:
        year_str, month_str = raw.split("-", 1)
        year = int(year_str)
        month_num = int(month_str)
        if month_num < 1 or month_num > 12 or len(year_str) != 4:
            raise ValueError
        # Reject things like 2026-9 (require zero-padded month) for a clear contract.
        if len(month_str) != 2:
            raise ValueError
        # Validate calendar date exists (also rejects absurd years via date()).
        date(year, month_num, 1)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid month. Use YYYY-MM (e.g. 2026-09).",
        ) from exc

    return year, month_num, f"{year:04d}-{month_num:02d}"


def month_bounds(year: int, month: int) -> tuple[date, date]:
    """Return [start, end) for the month. end is the first day of the next month."""
    start = date(year, month, 1)
    if month == 12:
        end = date(year + 1, 1, 1)
    else:
        end = date(year, month + 1, 1)
    return start, end


def previous_month(year: int, month: int) -> tuple[int, int]:
    if month == 1:
        return year - 1, 12
    return year, month - 1


def _base_filters(
    start: date,
    end: date,
    account_id: int | None,
):
    filters = [
        Transaction.date >= start,
        Transaction.date < end,
    ]
    if account_id is not None:
        filters.append(Transaction.account_id == account_id)
    return filters


def _month_totals(
    db: Session,
    start: date,
    end: date,
    account_id: int | None,
) -> tuple[Decimal, Decimal, Decimal, int]:
    filters = _base_filters(start, end, account_id)

    income_expr = func.coalesce(
        func.sum(case((Transaction.amount > 0, Transaction.amount), else_=0)),
        0,
    )
    spending_expr = func.coalesce(
        func.sum(case((Transaction.amount < 0, -Transaction.amount), else_=0)),
        0,
    )
    net_expr = func.coalesce(func.sum(Transaction.amount), 0)
    count_expr = func.count(Transaction.id)

    row = db.execute(
        select(income_expr, spending_expr, net_expr, count_expr).where(*filters)
    ).one()

    return (
        _quantize_money(row[0]),
        _quantize_money(row[1]),
        _quantize_money(row[2]),
        int(row[3] or 0),
    )


def _spending_by_category(
    db: Session,
    start: date,
    end: date,
    account_id: int | None,
    total_spending: Decimal,
) -> list[CategorySpending]:
    filters = _base_filters(start, end, account_id)
    filters.append(Transaction.amount < 0)

    # Categories are canonicalized at write time; keep empty→uncategorized as a safety net.
    category_label = case(
        (func.trim(Transaction.category) == "", "uncategorized"),
        else_=Transaction.category,
    )
    amount_expr = func.sum(-Transaction.amount)

    rows = db.execute(
        select(category_label, amount_expr)
        .where(*filters)
        .group_by(category_label)
        .order_by(amount_expr.desc())
    ).all()

    results: list[CategorySpending] = []
    for category, amount in rows:
        money = _quantize_money(amount)
        if total_spending > 0:
            percent = _quantize_percent((money / total_spending) * Decimal("100"))
        else:
            percent = ZERO
        results.append(
            CategorySpending(
                category=str(category),
                amount=money,
                percent_of_spending=percent,
            )
        )
    return results


def _top_merchants(
    db: Session,
    start: date,
    end: date,
    account_id: int | None,
) -> list[MerchantSpending]:
    filters = _base_filters(start, end, account_id)
    filters.append(Transaction.amount < 0)

    amount_expr = func.sum(-Transaction.amount)
    count_expr = func.count(Transaction.id)

    rows = db.execute(
        select(Transaction.merchant, amount_expr, count_expr)
        .where(*filters)
        .group_by(Transaction.merchant)
        .order_by(amount_expr.desc(), count_expr.desc())
        .limit(TOP_MERCHANTS_LIMIT)
    ).all()

    return [
        MerchantSpending(
            merchant=str(merchant),
            amount=_quantize_money(amount),
            transaction_count=int(count or 0),
        )
        for merchant, amount, count in rows
    ]


def _spending_change_percent(
    current: Decimal,
    previous: Decimal,
) -> Decimal | None:
    if previous == ZERO:
        if current == ZERO:
            return ZERO
        return None
    return _quantize_percent(((current - previous) / previous) * Decimal("100"))


def get_analytics_summary(
    db: Session,
    *,
    month: str | None = None,
    account_id: int | None = None,
) -> AnalyticsSummary:
    if account_id is not None:
        require_account(db, account_id)

    year, month_num, month_label = parse_month(month)
    start, end = month_bounds(year, month_num)
    prev_year, prev_month_num = previous_month(year, month_num)
    prev_start, prev_end = month_bounds(prev_year, prev_month_num)

    income, spending, net, count = _month_totals(db, start, end, account_id)
    _, prev_spending, _, _ = _month_totals(db, prev_start, prev_end, account_id)

    change_amount = _quantize_money(spending - prev_spending)
    change_percent = _spending_change_percent(spending, prev_spending)

    return AnalyticsSummary(
        month=month_label,
        total_income=income,
        total_spending=spending,
        net_cash_flow=net,
        transaction_count=count,
        previous_month=PreviousMonthComparison(
            total_spending=prev_spending,
            spending_change_amount=change_amount,
            spending_change_percent=change_percent,
        ),
        spending_by_category=_spending_by_category(
            db, start, end, account_id, spending
        ),
        top_merchants=_top_merchants(db, start, end, account_id),
    )
