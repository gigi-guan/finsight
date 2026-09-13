"""Deterministic / statistical recurring-transaction detection.

Computes recurring series from history. Does not persist is_recurring flags.
Confidence scores are explainable heuristics, not calibrated probabilities.
"""

from __future__ import annotations

import calendar
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from statistics import median
from typing import Iterable, Literal, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.transaction import Transaction
from app.schemas.recurring import RecurringSeries
from app.services.transaction import require_account
from app.services.transaction_normalize import normalize_merchant

Frequency = Literal["weekly", "biweekly", "monthly"]
AmountVariability = Literal["low", "medium", "high"]

MIN_OBSERVATIONS = 3
MIN_CONFIDENCE = Decimal("0.55")
MIN_INTERVAL_SCORE = 0.5

WEEKLY_TARGET = 7
WEEKLY_TOLERANCE = 2
BIWEEKLY_TARGET = 14
BIWEEKLY_TOLERANCE = 3
MONTHLY_DAY_TOLERANCE = 3

CENT = Decimal("0.01")
ZERO = Decimal("0")


@dataclass(frozen=True)
class TxPoint:
    account_id: int
    merchant: str
    date: date
    amount: Decimal
    category: str


def add_calendar_months(start: date, months: int) -> date:
    """Shift a date by calendar months, clamping the day into the target month."""
    month_index = start.month - 1 + months
    year = start.year + month_index // 12
    month = month_index % 12 + 1
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(start.day, last_day))


def _quantize_money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def _quantize_score(value: float | Decimal) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _day_deltas(dates: Sequence[date]) -> list[int]:
    return [(dates[i] - dates[i - 1]).days for i in range(1, len(dates))]


def _monthly_errors(dates: Sequence[date]) -> list[int]:
    errors: list[int] = []
    for i in range(1, len(dates)):
        expected = add_calendar_months(dates[i - 1], 1)
        errors.append(abs((dates[i] - expected).days))
    return errors


def _score_fixed_interval(
    deltas: Sequence[int],
    *,
    target: int,
    tolerance: int,
) -> float:
    if not deltas:
        return 0.0
    within = sum(1 for d in deltas if abs(d - target) <= tolerance)
    coverage = within / len(deltas)
    if coverage < 0.7:
        return 0.0
    mad = median(abs(d - target) for d in deltas)
    regularity = max(0.0, 1.0 - (mad / tolerance))
    return 0.5 * coverage + 0.5 * regularity


def _score_monthly(dates: Sequence[date]) -> float:
    errors = _monthly_errors(dates)
    if not errors:
        return 0.0
    within = sum(1 for e in errors if e <= MONTHLY_DAY_TOLERANCE)
    coverage = within / len(errors)
    if coverage < 0.7:
        # Fallback: day-span heuristic for near-monthly spacing
        deltas = _day_deltas(dates)
        return _score_fixed_interval(deltas, target=30, tolerance=5) * 0.85
    mad = median(errors)
    regularity = max(0.0, 1.0 - (mad / MONTHLY_DAY_TOLERANCE))
    return 0.5 * coverage + 0.5 * regularity


def detect_frequency(dates: Sequence[date]) -> tuple[Frequency | None, float]:
    """Return best-matching frequency and interval_score in [0, 1]."""
    if len(dates) < MIN_OBSERVATIONS:
        return None, 0.0
    ordered = sorted(dates)
    deltas = _day_deltas(ordered)
    candidates: list[tuple[Frequency, float]] = [
        ("weekly", _score_fixed_interval(deltas, target=WEEKLY_TARGET, tolerance=WEEKLY_TOLERANCE)),
        (
            "biweekly",
            _score_fixed_interval(
                deltas, target=BIWEEKLY_TARGET, tolerance=BIWEEKLY_TOLERANCE
            ),
        ),
        ("monthly", _score_monthly(ordered)),
    ]
    frequency, score = max(candidates, key=lambda item: item[1])
    if score < MIN_INTERVAL_SCORE:
        return None, score
    return frequency, score


def amount_variability(amounts: Sequence[Decimal]) -> tuple[AmountVariability, float]:
    """Classify amount stability using Decimal relative range on absolute values."""
    abs_amounts = [abs(a) for a in amounts]
    mean = sum(abs_amounts) / Decimal(len(abs_amounts))
    if mean == ZERO:
        return "low", 1.0
    spread = max(abs_amounts) - min(abs_amounts)
    relative = spread / mean
    if relative <= Decimal("0.02"):
        return "low", 1.0
    if relative <= Decimal("0.20"):
        return "medium", 0.6
    return "high", 0.25


def heuristic_confidence(
    *,
    n: int,
    interval_score: float,
    amount_score: float,
    same_sign: bool,
) -> Decimal:
    """Explainable recurrence score in [0, 1] — not a calibrated probability.

    confidence = 0.35*interval + 0.25*amount + 0.25*count + 0.15*sign
    count_score rises from 0 at n=3 toward 1 by n=6.
    """
    count_score = min(max(n - MIN_OBSERVATIONS, 0) / 3.0, 1.0)
    sign_score = 1.0 if same_sign else 0.0
    raw = (
        0.35 * interval_score
        + 0.25 * amount_score
        + 0.25 * count_score
        + 0.15 * sign_score
    )
    return min(Decimal("1.00"), max(ZERO, _quantize_score(raw)))


def expected_next_date(last: date, frequency: Frequency) -> date:
    if frequency == "weekly":
        return last + timedelta(days=WEEKLY_TARGET)
    if frequency == "biweekly":
        return last + timedelta(days=BIWEEKLY_TARGET)
    return add_calendar_months(last, 1)


def _majority_category(categories: Sequence[str]) -> str:
    counts = Counter(categories)
    return counts.most_common(1)[0][0]


def detect_recurring_series(transactions: Iterable[TxPoint]) -> list[RecurringSeries]:
    """Pure detection over in-memory transactions (DB or fixtures)."""
    grouped: dict[tuple[int, str], list[TxPoint]] = defaultdict(list)
    for tx in transactions:
        key = (tx.account_id, normalize_merchant(tx.merchant))
        grouped[key].append(tx)

    results: list[RecurringSeries] = []
    for (account_id, norm_merchant), points in grouped.items():
        if len(points) < MIN_OBSERVATIONS:
            continue
        points_sorted = sorted(points, key=lambda p: (p.date, p.merchant))
        dates = [p.date for p in points_sorted]
        # One transaction per day for interval stability (keep last amount that day).
        by_day: dict[date, TxPoint] = {}
        for p in points_sorted:
            by_day[p.date] = p
        deduped = [by_day[d] for d in sorted(by_day)]
        if len(deduped) < MIN_OBSERVATIONS:
            continue

        dates = [p.date for p in deduped]
        amounts = [p.amount for p in deduped]
        frequency, interval_score = detect_frequency(dates)
        if frequency is None:
            continue

        variability, amount_score = amount_variability(amounts)
        signs = {1 if a > 0 else -1 if a < 0 else 0 for a in amounts}
        same_sign = len(signs - {0}) == 1
        confidence = heuristic_confidence(
            n=len(deduped),
            interval_score=interval_score,
            amount_score=amount_score,
            same_sign=same_sign,
        )
        if confidence < MIN_CONFIDENCE or interval_score < MIN_INTERVAL_SCORE:
            continue

        avg = _quantize_money(sum(amounts) / Decimal(len(amounts)))
        last = deduped[-1]
        display_merchant = last.merchant
        results.append(
            RecurringSeries(
                merchant=display_merchant,
                normalized_merchant=norm_merchant,
                account_id=account_id,
                category=_majority_category([p.category for p in deduped]),
                frequency=frequency,
                transaction_count=len(deduped),
                average_amount=avg,
                amount_variability=variability,
                last_date=last.date,
                expected_next_date=expected_next_date(last.date, frequency),
                confidence=confidence,
            )
        )

    results.sort(
        key=lambda s: (s.confidence, s.transaction_count, s.merchant.casefold()),
        reverse=True,
    )
    return results


def load_tx_points(
    db: Session,
    account_id: int | None = None,
) -> list[TxPoint]:
    if account_id is not None:
        require_account(db, account_id)
    statement = select(Transaction)
    if account_id is not None:
        statement = statement.where(Transaction.account_id == account_id)
    rows = db.scalars(statement).all()
    return [
        TxPoint(
            account_id=row.account_id,
            merchant=row.merchant,
            date=row.date,
            amount=row.amount,
            category=row.category,
        )
        for row in rows
    ]


def get_recurring_series(
    db: Session,
    account_id: int | None = None,
) -> list[RecurringSeries]:
    return detect_recurring_series(load_tx_points(db, account_id=account_id))
