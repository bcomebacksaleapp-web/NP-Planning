from app.core.models.party import Customer, Site
from app.domain.archiving import archive, is_archived, unarchive


def test_archive_sets_timestamp_but_row_survives(session):
    customer = Customer(name="Acme Co")
    session.add(customer)
    session.flush()

    archive(session, customer)
    session.commit()

    # Row still exists and is still queryable -- archiving is not deletion (Law 5).
    fetched = session.get(Customer, customer.id)
    assert fetched is not None
    assert is_archived(fetched)
    assert fetched.archived_at is not None


def test_unarchive_clears_timestamp(session):
    customer = Customer(name="Acme Co")
    session.add(customer)
    session.flush()
    archive(session, customer)
    session.flush()

    unarchive(session, customer)
    session.commit()

    assert not is_archived(customer)
    assert customer.archived_at is None


def test_archive_is_idempotent(session):
    customer = Customer(name="Acme Co")
    session.add(customer)
    session.flush()

    archive(session, customer)
    first_timestamp = customer.archived_at

    archive(session, customer)  # calling twice must not bump the timestamp
    assert customer.archived_at == first_timestamp


def test_archiving_customer_does_not_cascade_to_its_sites(session):
    """Archiving a parent is a fact about the parent, not an instruction to its children."""
    customer = Customer(name="Acme Co")
    session.add(customer)
    session.flush()
    site = Site(customer_id=customer.id, site_type="FACTORY", name="Factory A")
    session.add(site)
    session.flush()

    archive(session, customer)
    session.commit()

    session.refresh(site)
    assert not is_archived(site)
