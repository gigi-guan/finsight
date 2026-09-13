"""Account domain service — DB operations used by API routes."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.account import Account
from app.schemas.account import AccountCreate


def create_account(db: Session, data: AccountCreate) -> Account:
    account = Account(
        name=data.name,
        account_type=data.account_type,
        institution=data.institution,
        current_balance=data.current_balance,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


def list_accounts(db: Session) -> list[Account]:
    statement = select(Account).order_by(Account.id)
    return list(db.scalars(statement).all())
