from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.db import get_db
from app.domain.business_health import (
    healthy_sites_summary,
    pipeline_by_state,
    product_performance_summary,
    quote_gm_summary,
    revenue_summary,
    site_capture_summary,
    supplier_concentration_summary,
)

router = APIRouter(prefix="/business", tags=["business"])


@router.get("/health")
def business_health_route(
    as_of: datetime | None = None,
    db: Session = Depends(get_db),
    _user=Depends(require_permission("business_health", "READ")),
) -> dict:
    """Part 14's Business Health view, all six aggregations built across Sprints 1.3-Phase 3.
    `as_of` (Part 14.15 Business Time Travel) reflects the business as it stood at that point
    in time for the revision-aware views (quote_gm_summary/product_performance_summary/
    revenue_summary); site_capture_summary/healthy_sites_summary/supplier_concentration_summary
    are current-state-only views with no revision history to travel through.
    """
    return {
        "pipeline_by_state": pipeline_by_state(db),
        "quote_gm_summary": quote_gm_summary(db, as_of=as_of),
        "revenue_summary": revenue_summary(db, as_of=as_of),
        "product_performance_summary": product_performance_summary(db, as_of=as_of),
        "site_capture_summary": site_capture_summary(db),
        "healthy_sites_summary": healthy_sites_summary(db),
        "supplier_concentration_summary": supplier_concentration_summary(db),
    }
