"""Transaction HTTP endpoints."""

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.transaction import (
    TransactionCategoryUpdate,
    TransactionCreate,
    TransactionImportResult,
    TransactionRead,
)
from app.services import transaction as transaction_service
from app.services import transaction_import as transaction_import_service

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.post("", response_model=TransactionRead, status_code=status.HTTP_201_CREATED)
def create_transaction(
    payload: TransactionCreate,
    db: Session = Depends(get_db),
) -> TransactionRead:
    return transaction_service.create_transaction(db, payload)


@router.get("", response_model=list[TransactionRead])
def get_transactions(
    account_id: int | None = Query(
        default=None,
        gt=0,
        description="Optional account filter",
    ),
    db: Session = Depends(get_db),
) -> list[TransactionRead]:
    return transaction_service.list_transactions(db, account_id=account_id)


@router.patch("/{transaction_id}/category", response_model=TransactionRead)
def update_transaction_category(
    transaction_id: int,
    payload: TransactionCategoryUpdate,
    db: Session = Depends(get_db),
) -> TransactionRead:
    """Update only categorization. Server sets source=user and clears confidence."""
    return transaction_service.update_transaction_category(
        db,
        transaction_id,
        payload,
    )


@router.post(
    "/import",
    response_model=TransactionImportResult,
    status_code=status.HTTP_200_OK,
)
def import_transactions(
    account_id: int = Form(..., gt=0),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> TransactionImportResult:
    """Upload a CSV of transactions for an existing account (partial success).

    Sync route: matches sibling endpoints and the sync SQLAlchemy Session used
    for parse/persist. Upload bytes are read from the SpooledTemporaryFile.
    """
    return transaction_import_service.import_transactions_from_csv(
        db,
        account_id=account_id,
        file=file,
    )
