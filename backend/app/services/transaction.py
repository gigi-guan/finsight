"""Transaction domain service — DB operations used by API routes."""

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.account import Account
from app.models.transaction import Transaction
from app.schemas.transaction import (
    TransactionCategoryUpdate,
    TransactionCreate,
    TransactionRead,
)
from app.services.transaction_normalize import normalize_category


def _to_read(transaction: Transaction) -> TransactionRead:
    return TransactionRead(
        id=transaction.id,
        account_id=transaction.account_id,
        account_name=transaction.account.name,
        date=transaction.date,
        merchant=transaction.merchant,
        description=transaction.description,
        amount=transaction.amount,
        category=transaction.category,
        category_source=transaction.category_source,  # type: ignore[arg-type]
        category_confidence=transaction.category_confidence,
        created_at=transaction.created_at,
    )


def _require_transaction(db: Session, transaction_id: int) -> Transaction:
    transaction = db.scalars(
        select(Transaction)
        .options(joinedload(Transaction.account))
        .where(Transaction.id == transaction_id)
    ).first()
    if transaction is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction with id {transaction_id} was not found.",
        )
    return transaction


def _require_account(db: Session, account_id: int) -> Account:
    account = db.get(Account, account_id)
    if account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account with id {account_id} was not found.",
        )
    return account


def require_account(db: Session, account_id: int) -> Account:
    """Public alias used by import and other account-scoped operations."""
    return _require_account(db, account_id)


def create_transaction(db: Session, data: TransactionCreate) -> TransactionRead:
    account = _require_account(db, data.account_id)
    transaction = Transaction(
        account_id=account.id,
        date=data.date,
        merchant=data.merchant.strip(),
        description=data.description.strip(),
        amount=data.amount,
        category=normalize_category(data.category),
        category_source="user",
        category_confidence=None,
    )
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    # Ensure relationship is loaded for account_name in the response.
    transaction.account = account
    return _to_read(transaction)


def list_transactions(
    db: Session,
    account_id: int | None = None,
) -> list[TransactionRead]:
    if account_id is not None:
        _require_account(db, account_id)

    statement = (
        select(Transaction)
        .options(joinedload(Transaction.account))
        .order_by(Transaction.date.desc(), Transaction.id.desc())
    )
    if account_id is not None:
        statement = statement.where(Transaction.account_id == account_id)

    transactions = db.scalars(statement).unique().all()
    return [_to_read(transaction) for transaction in transactions]


def update_transaction_category(
    db: Session,
    transaction_id: int,
    data: TransactionCategoryUpdate,
) -> TransactionRead:
    """Assign/correct a category. Always records a trusted user label."""
    transaction = _require_transaction(db, transaction_id)
    transaction.category = normalize_category(data.category)
    transaction.category_source = "user"
    transaction.category_confidence = None
    db.commit()
    db.refresh(transaction)
    return _to_read(transaction)
