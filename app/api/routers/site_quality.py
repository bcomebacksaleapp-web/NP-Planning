import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.db import get_db
from app.core.models.site_quality_flag import SiteQualityFlag
from app.domain.site_quality import active_flags_for_site, flag_site, is_healthy, resolve_flag

router = APIRouter(tags=["site-quality"])


class FlagSiteRequest(BaseModel):
    flag_type: str
    description: str
    flagged_by: str


class FlagResponse(BaseModel):
    id: uuid.UUID
    flag_type: str
    description: str
    resolved: bool


class SiteHealthResponse(BaseModel):
    is_healthy: bool
    active_flags: list[FlagResponse]


@router.post("/sites/{site_id}/quality-flags", response_model=FlagResponse)
def flag_site_route(
    site_id: uuid.UUID,
    body: FlagSiteRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("site_quality_flag", "DRAFT")),
) -> FlagResponse:
    flag = flag_site(db, site_id, body.flag_type, body.description, body.flagged_by, actor_user_id=user.id)
    db.commit()
    return FlagResponse(id=flag.id, flag_type=flag.flag_type, description=flag.description, resolved=False)


@router.get("/sites/{site_id}/quality", response_model=SiteHealthResponse)
def site_health_route(
    site_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("site_quality_flag", "READ")),
) -> SiteHealthResponse:
    flags = active_flags_for_site(db, site_id)
    return SiteHealthResponse(
        is_healthy=is_healthy(db, site_id),
        active_flags=[FlagResponse(id=f.id, flag_type=f.flag_type, description=f.description, resolved=False) for f in flags],
    )


@router.post("/quality-flags/{flag_id}/resolve", response_model=FlagResponse)
def resolve_flag_route(
    flag_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("site_quality_flag", "DRAFT")),
) -> FlagResponse:
    flag = db.get(SiteQualityFlag, flag_id)
    if flag is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Flag not found")

    resolve_flag(db, flag, actor_user_id=user.id)
    db.commit()
    return FlagResponse(id=flag.id, flag_type=flag.flag_type, description=flag.description, resolved=True)
