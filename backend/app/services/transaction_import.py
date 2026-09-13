"""CSV transaction import — parse, validate, dedupe, and persist in one commit."""

from __future__ import annotations

import csv
import io
from typing import Any

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.transaction import Transaction
from app.schemas.transaction import TransactionImportError, TransactionImportResult
from app.services.transaction import require_account
from app.services.transaction_normalize import (
    DuplicateKey,
    duplicate_key,
    normalize_category,
    parse_amount,
    parse_date,
)

MAX_CSV_BYTES = 2 * 1024 * 1024  # 2 MiB
REQUIRED_HEADERS = {"date", "merchant", "amount"}


def _normalize_row_dict(row: dict[str, Any | None]) -> dict[str, str]:
    """Map header names case-insensitively to trimmed string cells."""
    by_name: dict[str, str] = {}
    for key, value in row.items():
        if key is None:
            continue
        by_name[key.strip().casefold()] = "" if value is None else str(value).strip()
    return by_name


def _validate_headers(fieldnames: list[str] | None) -> None:
    if not fieldnames:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CSV is missing a header row.",
        )
    normalized = {name.strip().casefold() for name in fieldnames if name}
    missing = REQUIRED_HEADERS - normalized
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"CSV is missing required columns: {', '.join(sorted(missing))}.",
        )


async def import_transactions_from_csv(
    db: Session,
    account_id: int,
    file: UploadFile,
) -> TransactionImportResult:
    account = require_account(db, account_id)

    filename = (file.filename or "").lower()
    if filename and not (filename.endswith(".csv") or filename.endswith(".txt")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upload a .csv file.",
        )

    raw = await file.read()
    if not raw:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )
    if len(raw) > MAX_CSV_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"CSV exceeds maximum size of {MAX_CSV_BYTES} bytes.",
        )

    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CSV must be UTF-8 encoded.",
        ) from exc

    try:
        reader = csv.DictReader(io.StringIO(text))
        _validate_headers(reader.fieldnames)
    except HTTPException:
        raise
    except csv.Error as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not parse CSV: {exc}",
        ) from exc

    existing_rows = db.scalars(
        select(Transaction).where(Transaction.account_id == account.id)
    ).all()
    seen_keys: set[DuplicateKey] = {
        duplicate_key(
            account.id,
            row.date,
            row.merchant,
            row.amount,
            row.description,
        )
        for row in existing_rows
    }

    total_rows = 0
    rejected = 0
    duplicates = 0
    errors: list[TransactionImportError] = []
    to_insert: list[Transaction] = []

    try:
        for index, raw_row in enumerate(reader, start=2):  # row 1 = header
            if raw_row is None or all(
                (value is None or str(value).strip() == "")
                for value in raw_row.values()
            ):
                continue

            total_rows += 1
            row = _normalize_row_dict(raw_row)

            date_raw = row.get("date", "")
            merchant = row.get("merchant", "")
            amount_raw = row.get("amount", "")
            # Optional fields: empty string when absent (not invented labels).
            description = row.get("description", "")
            category_raw = row.get("category", "")

            if not date_raw:
                rejected += 1
                errors.append(
                    TransactionImportError(
                        row=index, field="date", message="Missing required value"
                    )
                )
                continue
            if not merchant:
                rejected += 1
                errors.append(
                    TransactionImportError(
                        row=index, field="merchant", message="Blank merchant"
                    )
                )
                continue
            if not amount_raw:
                rejected += 1
                errors.append(
                    TransactionImportError(
                        row=index, field="amount", message="Missing required value"
                    )
                )
                continue

            if len(merchant) > 255:
                rejected += 1
                errors.append(
                    TransactionImportError(
                        row=index, field="merchant", message="Merchant is too long"
                    )
                )
                continue
            if len(description) > 500:
                rejected += 1
                errors.append(
                    TransactionImportError(
                        row=index,
                        field="description",
                        message="Description is too long",
                    )
                )
                continue
            if len(category_raw) > 100:
                rejected += 1
                errors.append(
                    TransactionImportError(
                        row=index, field="category", message="Category is too long"
                    )
                )
                continue

            try:
                tx_date = parse_date(date_raw)
            except ValueError as exc:
                rejected += 1
                errors.append(
                    TransactionImportError(row=index, field="date", message=str(exc))
                )
                continue

            try:
                amount = parse_amount(amount_raw)
            except ValueError as exc:
                rejected += 1
                errors.append(
                    TransactionImportError(row=index, field="amount", message=str(exc))
                )
                continue

            category = normalize_category(category_raw)

            key = duplicate_key(account.id, tx_date, merchant, amount, description)
            if key in seen_keys:
                duplicates += 1
                errors.append(
                    TransactionImportError(
                        row=index,
                        field=None,
                        message="Duplicate of an existing or earlier row in this file",
                    )
                )
                continue

            seen_keys.add(key)
            to_insert.append(
                Transaction(
                    account_id=account.id,
                    date=tx_date,
                    merchant=merchant,
                    description=description,
                    amount=amount,
                    category=category,
                    category_source="csv",
                    category_confidence=None,
                )
            )
    except csv.Error as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not parse CSV: {exc}",
        ) from exc

    if to_insert:
        db.add_all(to_insert)
        db.commit()

    return TransactionImportResult(
        total_rows=total_rows,
        imported=len(to_insert),
        rejected=rejected,
        duplicates=duplicates,
        errors=errors,
    )
