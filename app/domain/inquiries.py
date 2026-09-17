import uuid

from sqlalchemy import select

from app.core.models.inquiry import WebsiteInquiry
from app.core.models.opportunity import Opportunity
from app.core.models.party import Customer, Site
from app.domain.events import record_event
from app.domain.opportunities import create_opportunity
from app.domain.site import create_site, get_or_create_customer


class InquiryAlreadyConvertedError(Exception):
    pass


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


def convert_inquiry_to_opportunity(
    session,
    inquiry: WebsiteInquiry,
    customer_name: str,
    site_type: str,
    site_name: str,
    site_address: str | None = None,
    actor_user_id: uuid.UUID | None = None,
) -> tuple[Customer, Site, Opportunity]:
    """The manual step the editor's Inquiries tab used to just describe in prose ("done
    elsewhere in the system") -- now a real action. A raw inquiry has no Site yet (see
    WebsiteInquiry's docstring), so this is the one place that bridges the two: get-or-create
    the Customer, create a real Site under it, then a real Opportunity under that Site, exactly
    the same domain calls POST /sites and POST /opportunities use individually. The staff member
    supplies customer_name/site_type/site_name themselves rather than this function guessing --
    an inquiry's free-text service_interest is not a reliable site_type, and inventing one would
    violate the project's real-data-only rule.
    """
    if inquiry.converted_to_opportunity_id is not None:
        raise InquiryAlreadyConvertedError("Inquiry has already been converted")

    customer = get_or_create_customer(session, customer_name, actor_user_id)
    site = create_site(session, customer.id, site_type, site_name, site_address, actor_user_id)
    opportunity = create_opportunity(
        session, site.id, "website_inquiry", inquiry.message or inquiry.service_interest
    )

    inquiry.converted_to_opportunity_id = opportunity.id
    session.flush()
    record_event(
        session, "website_inquiry", inquiry.id, "converted_to_opportunity",
        {"opportunity_id": str(opportunity.id), "site_id": str(site.id), "customer_id": str(customer.id)},
        actor_user_id,
    )
    return customer, site, opportunity
