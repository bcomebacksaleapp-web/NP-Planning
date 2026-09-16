import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.models.website import WebsiteBranch, WebsitePage, WebsitePageRevision, WidgetInstance
from app.domain.events import record_event
from app.domain.revisioning import latest_revision, next_revision_number

# The 3 brand themes from the Website Studio design mockups. Each is a color palette + heading
# font pairing (site.html applies the CSS side via [data-brand-theme]); Thai body copy always
# stays Cordia New regardless of theme -- see the project's Thai-font rule.
BRAND_THEMES = {"modern-industrial", "dark-pro", "minimal-architect"}


def get_branch(session: Session, branch_name: str) -> WebsiteBranch | None:
    """Branch-level info (currently just the brand theme) for anything that needs to know a
    branch's identity without going through a specific page -- the public site renderer applying
    the theme, or the editor's Design tab."""
    return session.execute(select(WebsiteBranch).where(WebsiteBranch.name == branch_name)).scalar_one_or_none()


def set_branch_theme(
    session: Session, branch: WebsiteBranch, theme: str, actor_user_id: uuid.UUID | None = None
) -> WebsiteBranch:
    if theme not in BRAND_THEMES:
        raise ValueError(f"Unknown theme {theme!r}; must be one of {sorted(BRAND_THEMES)}")
    branch.theme = theme
    session.flush()
    record_event(session, "website_branch", branch.id, "theme_changed", {"theme": theme}, actor_user_id)
    return branch


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


def list_pages(session: Session, branch_name: str) -> list[WebsitePage]:
    """Which pages exist under a branch, by slug -- needed by anything that has to let someone
    pick a page (an editor's page list, a sitemap) rather than already knowing the exact slug
    to fetch, which get_published_page assumes."""
    return list(
        session.execute(
            select(WebsitePage)
            .join(WebsiteBranch, WebsiteBranch.id == WebsitePage.branch_id)
            .where(WebsiteBranch.name == branch_name, WebsitePage.archived_at.is_(None))
            .order_by(WebsitePage.slug)
        ).scalars()
    )


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
