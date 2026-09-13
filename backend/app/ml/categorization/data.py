"""Load and filter labeled transactions for offline categorization experiments."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.transaction import Transaction
from app.services.transaction_normalize import normalize_merchant

TRUSTED_SOURCES = frozenset({"user", "csv"})
EXCLUDED_CATEGORIES = frozenset({"uncategorized", "other"})

# Heuristic thresholds for "enough data for meaningful evaluation"
MIN_USABLE_ROWS = 30
MIN_CLASSES = 3
MIN_MERCHANTS_PER_CLASS = 2

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
SYNTHETIC_FIXTURE_PATH = FIXTURES_DIR / "synthetic_labeled_transactions.json"


@dataclass(frozen=True)
class LabeledExample:
    merchant: str
    description: str
    category: str
    category_source: str
    merchant_group: str
    origin: str  # "real" | "synthetic"


def is_trusted_label(category_source: str, category: str) -> bool:
    """Return True if a row is eligible for supervised training/eval."""
    return (
        category_source in TRUSTED_SOURCES
        and category not in EXCLUDED_CATEGORIES
    )


def merchant_group_key(merchant: str) -> str:
    return normalize_merchant(merchant)


def filter_labeled_rows(
    rows: Iterable[dict[str, Any]],
    *,
    origin: str,
) -> list[LabeledExample]:
    examples: list[LabeledExample] = []
    for row in rows:
        source = str(row.get("category_source", ""))
        category = str(row.get("category", ""))
        if not is_trusted_label(source, category):
            continue
        merchant = str(row.get("merchant", ""))
        description = str(row.get("description", "") or "")
        examples.append(
            LabeledExample(
                merchant=merchant,
                description=description,
                category=category,
                category_source=source,
                merchant_group=merchant_group_key(merchant),
                origin=origin,
            )
        )
    return examples


def summarize_examples(examples: Sequence[LabeledExample]) -> dict[str, Any]:
    by_category: dict[str, int] = {}
    merchants_by_category: dict[str, set[str]] = {}
    for ex in examples:
        by_category[ex.category] = by_category.get(ex.category, 0) + 1
        merchants_by_category.setdefault(ex.category, set()).add(ex.merchant_group)

    return {
        "total": len(examples),
        "by_category": dict(sorted(by_category.items())),
        "unique_merchants": len({ex.merchant_group for ex in examples}),
        "merchants_per_category": {
            cat: len(merchants)
            for cat, merchants in sorted(merchants_by_category.items())
        },
        "classes": sorted(by_category),
    }


def has_sufficient_data(summary: dict[str, Any]) -> bool:
    if summary["total"] < MIN_USABLE_ROWS:
        return False
    if len(summary["classes"]) < MIN_CLASSES:
        return False
    merchants_per = summary["merchants_per_category"]
    if any(count < MIN_MERCHANTS_PER_CLASS for count in merchants_per.values()):
        return False
    return True


def load_real_examples(db: Session | None = None) -> list[LabeledExample]:
    """Load trusted labels from PostgreSQL without mutating rows."""
    own_session = db is None
    if own_session:
        engine = create_engine(get_settings().database_url)
        db = Session(engine)
    try:
        rows = db.execute(
            select(
                Transaction.merchant,
                Transaction.description,
                Transaction.category,
                Transaction.category_source,
            )
        ).mappings().all()
        payload = [dict(row) for row in rows]
        return filter_labeled_rows(payload, origin="real")
    finally:
        if own_session:
            db.close()


def load_synthetic_examples(
    path: Path | None = None,
) -> list[LabeledExample]:
    fixture_path = path or SYNTHETIC_FIXTURE_PATH
    data = json.loads(fixture_path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("Synthetic fixture must be a JSON list")
    return filter_labeled_rows(data, origin="synthetic")


def report_label_inventory(db: Session | None = None) -> dict[str, Any]:
    """Report trustworthy label counts for the real database (no training)."""
    own_session = db is None
    if own_session:
        engine = create_engine(get_settings().database_url)
        db = Session(engine)
    try:
        rows = db.execute(
            select(
                Transaction.merchant,
                Transaction.description,
                Transaction.category,
                Transaction.category_source,
            )
        ).mappings().all()
        payload = [dict(row) for row in rows]
    finally:
        if own_session:
            db.close()

    user_rows = [r for r in payload if r["category_source"] == "user"]
    csv_rows = [r for r in payload if r["category_source"] == "csv"]
    usable = filter_labeled_rows(payload, origin="real")
    usable_summary = summarize_examples(usable)

    return {
        "total_transactions": len(payload),
        "user_labeled_rows": len(user_rows),
        "csv_labeled_rows": len(csv_rows),
        "usable_training_rows": usable_summary["total"],
        "usable_by_category": usable_summary["by_category"],
        "unique_merchants_by_category": usable_summary["merchants_per_category"],
        "sufficient_for_retraining": has_sufficient_data(usable_summary),
        "retraining_threshold": {
            "min_usable_rows": MIN_USABLE_ROWS,
            "min_classes": MIN_CLASSES,
            "min_merchants_per_class": MIN_MERCHANTS_PER_CLASS,
        },
    }


def print_label_inventory() -> None:
    inventory = report_label_inventory()
    print(json.dumps(inventory, indent=2))
