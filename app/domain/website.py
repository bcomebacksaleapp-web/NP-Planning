import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.models.website import WebsiteBranch, WebsitePage, WebsitePageRevision, WidgetInstance
from app.domain.events import record_event
from app.domain.revisioning import latest_revision, next_revision_number


def get_published_page(session: Session, branch_name: str, slug: str) -> WebsitePageRevision | None:
    """The read side for anything that renders a page -- a public site renderer, a preview
    pane, this session's demo Artifact. Returns the CURRENT revision (or None if no branch/page
    matches), never a specific old one; fetching a past revision is a separate, deliberate
    action, not something a page-render request should stumble into.
    """
    page = session.execute(
        select(WebsitePage)
        .join(WebsiteBranch, WebsiteBranch.id == WebsitePage.branch_id)
        .where(WebsiteBranch.name == branch_name, WebsitePage.slug == slug, WebsitePage.archived_at.is_(None))
    ).scalar_one_or_none()
    if page is None:
        return None
    return latest_revision(session, WebsitePageRevision, "page_id", page.id)


def create_branch(
    session: Session, name: str, forked_from_branch_id: uuid.UUID | None = None
) -> WebsiteBranch:
    branch = WebsiteBranch(name=name, forked_from_branch_id=forked_from_branch_id)
    session.add(branch)
    session.flush()
    record_event(session, "website_branch", branch.id, "created", {"name": name})
    return branch


def _build_widgets(widgets: list[dict]) -> list[WidgetInstance]:
    return [
        WidgetInstance(
            widget_type=w["widget_type"],
            order_index=w["order_index"],
            visibility_rule=w.get("visibility_rule"),
            content_source=w.get("content_source"),
            config=w.get("config", {}),
        )
        for w in widgets
    ]


def create_page(
    session: Session, branch_id: uuid.UUID, slug: str, widgets: list[dict], actor_user_id: uuid.UUID | None = None
) -> WebsitePage:
    page = WebsitePage(branch_id=branch_id, slug=slug)
    session.add(page)
    session.flush()

    revision = WebsitePageRevision(page_id=page.id, revision_number=1)
    revision.widgets = _build_widgets(widgets)
    session.add(revision)
    session.flush()
    record_event(session, "website_page", page.id, "created", {"revision_number": 1}, actor_user_id)
    return page


def update_page(
    session: Session, page: WebsitePage, widgets: list[dict], actor_user_id: uuid.UUID | None = None
) -> WebsitePageRevision:
    """Creates a new revision with the given widget layout. Never mutates an existing
    WebsitePageRevision or its WidgetInstance rows -- removing a widget from the layout means it
    simply isn't included in the NEW revision's widget list; the old revision (and its widget
    row) still exists, untouched, in history (Law 4)."""
    revision_number = next_revision_number(session, WebsitePageRevision, "page_id", page.id)
    revision = WebsitePageRevision(page_id=page.id, revision_number=revision_number)
    revision.widgets = _build_widgets(widgets)
    session.add(revision)
    session.flush()
    record_event(session, "website_page", page.id, "revision_created", {"revision_number": revision_number}, actor_user_id)
    return revision


def restore_page_revision(
    session: Session, page: WebsitePage, target_revision_number: int, actor_user_id: uuid.UUID | None = None
) -> WebsitePageRevision:
    """Law 4: restoring Rev N creates a NEW revision copying Rev N's widget layout. Never
    touches the old rows."""
    target = session.execute(
        select(WebsitePageRevision).where(
            WebsitePageRevision.page_id == page.id,
            WebsitePageRevision.revision_number == target_revision_number,
        )
    ).scalar_one()

    widgets = [
        {
            "widget_type": w.widget_type,
            "order_index": w.order_index,
            "visibility_rule": w.visibility_rule,
            "content_source": w.content_source,
            "config": dict(w.config),
        }
        for w in target.widgets
    ]
    new_revision_number = next_revision_number(session, WebsitePageRevision, "page_id", page.id)
    revision = WebsitePageRevision(
        page_id=page.id, revision_number=new_revision_number, restored_from_revision_number=target.revision_number
    )
    revision.widgets = _build_widgets(widgets)
    session.add(revision)
    session.flush()
    record_event(
        session,
        "website_page",
        page.id,
        "revision_restored",
        {"revision_number": new_revision_number, "restored_from_revision_number": target.revision_number},
        actor_user_id,
    )
    return revision
