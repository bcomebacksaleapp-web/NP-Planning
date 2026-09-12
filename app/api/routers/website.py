import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.db import get_db
from app.core.models.website import WebsitePage, WebsitePageRevision
from app.domain.revisioning import latest_revision
from app.domain.website import create_branch, create_page, restore_page_revision, update_page

router = APIRouter(prefix="/website", tags=["website"])


class CreateBranchRequest(BaseModel):
    name: str
    forked_from_branch_id: uuid.UUID | None = None


class BranchResponse(BaseModel):
    id: uuid.UUID
    name: str
    forked_from_branch_id: uuid.UUID | None


class WidgetInput(BaseModel):
    widget_type: str
    order_index: int
    visibility_rule: str | None = None
    content_source: str | None = None
    config: dict = {}


class CreatePageRequest(BaseModel):
    branch_id: uuid.UUID
    slug: str
    widgets: list[WidgetInput]


class UpdatePageRequest(BaseModel):
    widgets: list[WidgetInput]


class RestorePageRevisionRequest(BaseModel):
    target_revision_number: int


class WidgetOutput(BaseModel):
    widget_type: str
    order_index: int
    content_source: str | None


class PageRevisionResponse(BaseModel):
    page_id: uuid.UUID
    revision_number: int
    widgets: list[WidgetOutput]
    restored_from_revision_number: int | None


def _revision_response(page_id: uuid.UUID, revision: WebsitePageRevision) -> PageRevisionResponse:
    return PageRevisionResponse(
        page_id=page_id,
        revision_number=revision.revision_number,
        widgets=[WidgetOutput(widget_type=w.widget_type, order_index=w.order_index, content_source=w.content_source) for w in revision.widgets],
        restored_from_revision_number=revision.restored_from_revision_number,
    )


@router.post("/branches", response_model=BranchResponse)
def create_branch_route(
    body: CreateBranchRequest, db: Session = Depends(get_db), user=Depends(require_permission("website_page", "DRAFT"))
) -> BranchResponse:
    branch = create_branch(db, body.name, body.forked_from_branch_id)
    db.commit()
    return BranchResponse(id=branch.id, name=branch.name, forked_from_branch_id=branch.forked_from_branch_id)


@router.post("/pages", response_model=PageRevisionResponse)
def create_page_route(
    body: CreatePageRequest, db: Session = Depends(get_db), user=Depends(require_permission("website_page", "DRAFT"))
) -> PageRevisionResponse:
    page = create_page(db, body.branch_id, body.slug, [w.model_dump() for w in body.widgets], actor_user_id=user.id)
    db.commit()
    current = latest_revision(db, WebsitePageRevision, "page_id", page.id)
    return _revision_response(page.id, current)


@router.put("/pages/{page_id}", response_model=PageRevisionResponse)
def update_page_route(
    page_id: uuid.UUID, body: UpdatePageRequest, db: Session = Depends(get_db),
    user=Depends(require_permission("website_page", "DRAFT")),
) -> PageRevisionResponse:
    page = db.get(WebsitePage, page_id)
    if page is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Page not found")

    revision = update_page(db, page, [w.model_dump() for w in body.widgets], actor_user_id=user.id)
    db.commit()
    return _revision_response(page.id, revision)


@router.post("/pages/{page_id}/restore", response_model=PageRevisionResponse)
def restore_page_route(
    page_id: uuid.UUID, body: RestorePageRevisionRequest, db: Session = Depends(get_db),
    user=Depends(require_permission("website_page", "DRAFT")),
) -> PageRevisionResponse:
    page = db.get(WebsitePage, page_id)
    if page is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Page not found")

    revision = restore_page_revision(db, page, body.target_revision_number, actor_user_id=user.id)
    db.commit()
    return _revision_response(page.id, revision)
