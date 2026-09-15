import uuid

from sqlalchemy import select

from app.core.models.inquiry import WebsiteInquiry
from app.domain.events import record_event


def create_inquiry(
    session,
    name: str,
    phone: str | None = None,
    email: str | None = None,
    service_interest: str | None = None,
    message: str | None = None,
    source_page: str | None = None,
) -> WebsiteInquiry:
    """Deliberately no actor_user_id -- this is the one write path in the system a real,
    unauthenticated website visitor triggers directly. See WebsiteInquiry's docstring for why
    this isn't just create_opportunity with a placeholder Site."""
    inquiry = WebsiteInquiry(
        name=name, phone=phone, email=email, service_interest=service_interest,
        message=message, source_page=source_page,
    )
    session.add(inquiry)
    session.flush()
    record_event(session, "website_inquiry", inquiry.id, "created", {"source_page": source_page})
    return inquiry


def list_inquiries(session) -> list[WebsiteInquiry]:
    """Staff-side triage queue -- newest first, so a new submission is immediately visible at
    the top rather than requiring anyone to know to scroll."""
    return list(session.execute(select(WebsiteInquiry).order_by(WebsiteInquiry.created_at.desc())).scalars())
