"""add_category_provenance_and_account_date_index

Revision ID: 003_category_provenance
Revises: 002_create_transactions
Create Date: 2026-09-13 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003_category_provenance"
down_revision: Union[str, Sequence[str], None] = "002_create_transactions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Keep in sync with app.services.transaction_normalize (migration must be self-contained).
_CANONICAL = {
    "income",
    "housing",
    "groceries",
    "dining",
    "transportation",
    "travel",
    "shopping",
    "entertainment",
    "utilities",
    "healthcare",
    "subscriptions",
    "other",
    "uncategorized",
}

_ALIASES = {
    "grocery": "groceries",
    "groceries": "groceries",
    "food": "dining",
    "dining": "dining",
    "restaurant": "dining",
    "restaurants": "dining",
    "transport": "transportation",
    "transportation": "transportation",
    "transit": "transportation",
    "gas": "transportation",
    "fuel": "transportation",
    "health": "healthcare",
    "healthcare": "healthcare",
    "medical": "healthcare",
    "rent": "housing",
    "mortgage": "housing",
    "housing": "housing",
    "util": "utilities",
    "utility": "utilities",
    "utilities": "utilities",
    "sub": "subscriptions",
    "subscription": "subscriptions",
    "subscriptions": "subscriptions",
    "income": "income",
    "payroll": "income",
    "salary": "income",
    "shopping": "shopping",
    "entertainment": "entertainment",
    "travel": "travel",
    "other": "other",
    "uncategorized": "uncategorized",
}


def _normalize_category(raw: str | None) -> str:
    if raw is None:
        return "uncategorized"
    cleaned = " ".join(str(raw).strip().split())
    if not cleaned:
        return "uncategorized"
    key = cleaned.casefold()
    if key in _ALIASES:
        return _ALIASES[key]
    if key in _CANONICAL:
        return key
    return "other"


def upgrade() -> None:
    op.add_column(
        "transactions",
        sa.Column(
            "category_source",
            sa.String(length=20),
            nullable=False,
            server_default="unknown",
        ),
    )
    op.add_column(
        "transactions",
        sa.Column("category_confidence", sa.Numeric(precision=4, scale=3), nullable=True),
    )
    op.create_check_constraint(
        "ck_transactions_category_confidence_range",
        "transactions",
        "category_confidence IS NULL OR "
        "(category_confidence >= 0 AND category_confidence <= 1)",
    )

    # Backfill: legacy rows → source unknown; canonicalize category values.
    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id, category FROM transactions")).mappings().all()
    for row in rows:
        canonical = _normalize_category(row["category"])
        conn.execute(
            sa.text(
                "UPDATE transactions "
                "SET category = :category, category_source = 'unknown', "
                "category_confidence = NULL "
                "WHERE id = :id"
            ),
            {"category": canonical, "id": row["id"]},
        )

    op.create_index(
        "ix_transactions_account_id_date",
        "transactions",
        ["account_id", "date"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_transactions_account_id_date", table_name="transactions")
    op.drop_constraint(
        "ck_transactions_category_confidence_range",
        "transactions",
        type_="check",
    )
    op.drop_column("transactions", "category_confidence")
    op.drop_column("transactions", "category_source")
