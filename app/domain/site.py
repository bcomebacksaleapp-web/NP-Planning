import uuid

from sqlalchemy import select

from app.core.models.party import Customer, Site
from app.domain.events import record_event


def get_or_create_customer(session, name: str, actor_user_id: uuid.UUID | None = None) -> Customer:
    """Idempotent on `name`, same shape as app.domain.suppliers.get_or_create_supplier."""
    customer = session.execute(select(Customer).where(Customer.name == name)).scalar_one_or_none()
    if customer is not None:
        return customer
    customer = Customer(name=name)
    session.add(customer)
    session.flush()
    record_event(session, "customer", customer.id, "created", {"name": name}, actor_user_id)
    return customer


def create_site(
    session,
    customer_id: uuid.UUID,
    site_type: str,
    name: str,
    address: str | None = None,
    actor_user_id: uuid.UUID | None = None,
) -> Site:
    """Like create_critical_spec/create_supplier_quote before it, this didn't exist until
    exercising the API end-to-end (Canopy configurator, Opportunities, Site quality, Site
    knowledge -- every one of them takes a site_id) surfaced there was no way to create a Site
    through the API at all, only via direct DB access."""
    site = Site(customer_id=customer_id, site_type=site_type, name=name, address=address)
    session.add(site)
    session.flush()
    record_event(session, "site", site.id, "created", {"name": name, "site_type": site_type}, actor_user_id)
    return site
