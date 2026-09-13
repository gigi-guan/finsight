"""Account HTTP endpoints."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.account import AccountCreate, AccountRead
from app.services import account as account_service

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.post("", response_model=AccountRead, status_code=status.HTTP_201_CREATED)
def create_account(
    payload: AccountCreate,
    db: Session = Depends(get_db),
) -> AccountRead:
    account = account_service.create_account(db, payload)
    return AccountRead.model_validate(account)


@router.get("", response_model=list[AccountRead])
def get_accounts(db: Session = Depends(get_db)) -> list[AccountRead]:
    accounts = account_service.list_accounts(db)
    return [AccountRead.model_validate(account) for account in accounts]
