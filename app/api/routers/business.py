from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.db import get_db
from app.domain.business_health import pipeline_by_state, quote_gm_summary, revenue_summary

router = APIRouter(prefix="/business", tags=["business"])


@router.get("/health")
def business_health_route(
    db: Session = Depends(get_db), _user=Depends(require_permission("business_health", "READ"))
) -> dict:
    return {
        "pipeline_by_state": pipeline_by_state(db),
        "quote_gm_summary": quote_gm_summary(db),
        "revenue_summary": revenue_summary(db),
    }
