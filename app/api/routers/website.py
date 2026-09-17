import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.db import get_db
from app.core.models.website import WebsitePage, WebsitePageRevision
from app.domain.revisioning import latest_revision
from app.domain.website import (
    BRAND_THEMES,
    FONT_PAIRS,
    create_branch,
    create_page,
    get_branch,
    get_published_page,
    list_pages,
    restore_page_revision,
    set_branch_font_pair,
    set_branch_theme,
    update_page,
)

router = APIRouter(prefix="/website", tags=["website"])


class CreateBranchRequest(BaseModel):
    name: str
    forked_from_branch_id: uuid.UUID | None = None


class BranchInfoResponse(BaseModel):
    name: str
    theme: str
    font_pair: str


class SetBranchThemeRequest(BaseModel):
    theme: str


class SetBranchFontPairRequest(BaseModel):
    font_pair: str


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
    config: dict


class PageRevisionResponse(BaseModel):
    page_id: uuid.UUID
    revision_number: int
    widgets: list[WidgetOutput]
    restored_from_revision_number: int | None


def _revision_response(page_id: uuid.UUID, revision: WebsitePageRevision) -> PageRevisionResponse:
    return PageRevisionResponse(
        page_id=page_id,
        revision_number=revision.revision_number,
        widgets=[
            WidgetOutput(widget_type=w.widget_type, order_index=w.order_index, content_source=w.content_source, config=w.config)
            for w in revision.widgets
        ],
        restored_from_revision_number=revision.restored_from_revision_number,
    )


class PageSummary(BaseModel):
    id: uuid.UUID
    slug: str


@router.get("/branches/{branch_name}/pages", response_model=list[PageSummary])
def list_pages_route(
    branch_name: str, db: Session = Depends(get_db), user=Depends(require_permission("website_page", "READ")),
) -> list[PageSummary]:
    """For an editor's page picker -- knowing a branch's slugs is itself gated (unlike reading
    one already-known page, which is public) since it's authoring-side navigation, not what a
    site visitor needs."""
    return [PageSummary(id=p.id, slug=p.slug) for p in list_pages(db, branch_name)]


@router.get("/branches/{branch_name}", response_model=BranchInfoResponse)
def get_branch_route(branch_name: str, db: Session = Depends(get_db)) -> BranchInfoResponse:
    """Deliberately no auth, same reasoning as get_published_page_route -- the public site
    renderer needs a branch's brand theme to paint itself before a visitor has ever logged in."""
    branch = get_branch(db, branch_name)
    if branch is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Branch not found")
    return BranchInfoResponse(name=branch.name, theme=branch.theme, font_pair=branch.font_pair)


@router.put("/branches/{branch_name}/theme", response_model=BranchInfoResponse)
def set_branch_theme_route(
    branch_name: str, body: SetBranchThemeRequest, db: Session = Depends(get_db),
    user=Depends(require_permission("website_page", "DRAFT")),
) -> BranchInfoResponse:
    branch = get_branch(db, branch_name)
    if branch is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Branch not found")
    if body.theme not in BRAND_THEMES:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"theme must be one of {sorted(BRAND_THEMES)}")
    set_branch_theme(db, branch, body.theme, actor_user_id=user.id)
    db.commit()
    return BranchInfoResponse(name=branch.name, theme=branch.theme, font_pair=branch.font_pair)


@router.put("/branches/{branch_name}/font", response_model=BranchInfoResponse)
def set_branch_font_pair_route(
    branch_name: str, body: SetBranchFontPairRequest, db: Session = Depends(get_db),
    user=Depends(require_permission("website_page", "DRAFT")),
) -> BranchInfoResponse:
    """Independent of /theme on purpose -- see FONT_PAIRS' docstring. A caller can change color
    and typography in either order, or just one without the other."""
    branch = get_branch(db, branch_name)
    if branch is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Branch not found")
    if body.font_pair not in FONT_PAIRS:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"font_pair must be one of {sorted(FONT_PAIRS)}")
    set_branch_font_pair(db, branch, body.font_pair, actor_user_id=user.id)
    db.commit()
    return BranchInfoResponse(name=branch.name, theme=branch.theme, font_pair=branch.font_pair)


@router.get("/pages/{branch_name}/{slug}", response_model=PageRevisionResponse)
def get_published_page_route(branch_name: str, slug: str, db: Session = Depends(get_db)) -> PageRevisionResponse:
    """Deliberately no auth -- this is the read path a real visitor's browser (or a renderer
    acting on their behalf) hits to display a published page, not an internal CMS operation.
    Every other /website route is DRAFT-gated because it mutates content; this one only reads
    whatever the last DRAFT/COMMIT already published.
    """
    revision = get_published_page(db, branch_name, slug)
    if revision is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Page not found")
    return _revision_response(revision.page_id, revision)


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
