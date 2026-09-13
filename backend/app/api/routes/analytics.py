"""Analytics HTTP endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.analytics import AnalyticsSummary
from app.schemas.recurring import RecurringSeries
from app.services import analytics as analytics_service
from app.services import recurring as recurring_service

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary", response_model=AnalyticsSummary)
def get_analytics_summary(
    account_id: int | None = Query(default=None, gt=0),
    month: str | None = Query(
        default=None,
        description="Month in YYYY-MM format. Defaults to the current calendar month.",
    ),
    db: Session = Depends(get_db),
) -> AnalyticsSummary:
    return analytics_service.get_analytics_summary(
        db,
        month=month,
        account_id=account_id,
    )


@router.get("/recurring", response_model=list[RecurringSeries])
def get_recurring_series(
    account_id: int | None = Query(default=None, gt=0),
    db: Session = Depends(get_db),
) -> list[RecurringSeries]:
    """Detect likely recurring payments/income from transaction history.

    Results are computed on read (not stored). Confidence is a heuristic score.
    """
    return recurring_service.get_recurring_series(db, account_id=account_id)
