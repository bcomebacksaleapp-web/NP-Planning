import pytest
from sqlalchemy import select

from app.core.models.party import Customer, Site
from app.core.models.project import Project, ProjectRevision
from app.core.models.quote import Quote, QuoteRevision
from app.domain.canopy_configurator import configure_canopy_and_create_quote
from app.domain.fresh_price import PriceQuote
from app.domain.revisioning import latest_revision


def _make_site(session) -> Site:
    customer = Customer(name="Acme Co")
    session.add(customer)
    session.flush()
    site = Site(customer_id=customer.id, site_type="FACTORY", name="Factory A")
    session.add(site)
    session.flush()
    return site


def test_configuring_a_canopy_creates_real_rows_not_a_ui_only_object(session):
    """The Blueprint's own Phase 1 acceptance criterion, checked directly against the database:
    "Customer configuration must generate canonical business data, not UI-only data." """
    site = _make_site(session)

    project, quote = configure_canopy_and_create_quote(
        session, site.id, width_m=6.0, length_m=4.0, roof_cover="Metal Sheet", unit_cost_per_m2=1500.0
    )
    session.commit()

    # Re-fetch from the database by id -- proves these are real persisted rows, not just the
    # Python objects this call happened to return.
    fetched_project = session.get(Project, project.id)
    fetched_quote = session.get(Quote, quote.id)
    assert fetched_project is not None
    assert fetched_quote is not None
    assert fetched_quote.project_id == fetched_project.id


def test_configuration_inputs_are_captured_in_the_project_revision(session):
    site = _make_site(session)
    project, _ = configure_canopy_and_create_quote(
        session, site.id, width_m=6.0, length_m=4.0, roof_cover="Metal Sheet", unit_cost_per_m2=1500.0
    )
    session.commit()

    revision = latest_revision(session, ProjectRevision, "project_id", project.id)
    assert revision.data["product"] == "CANOPY"
    assert revision.data["width_m"] == 6.0
    assert revision.data["quantities"]["roof_area_m2"] == 24.0


def test_quote_true_cost_derives_from_computed_quantity_times_given_unit_cost(session):
    site = _make_site(session)
    _, quote = configure_canopy_and_create_quote(
        session, site.id, width_m=6.0, length_m=4.0, roof_cover="Metal Sheet", unit_cost_per_m2=1500.0
    )
    session.commit()

    current = latest_revision(session, QuoteRevision, "quote_id", quote.id)
    expected_area_with_waste = 24.0 * 1.05
    assert round(current.true_cost, 2) == round(expected_area_with_waste * 1500.0, 2)
    assert len(current.lines) == 1
    assert round(current.lines[0].quantity, 2) == round(expected_area_with_waste, 2)


def test_quote_line_is_linked_to_the_canopy_product(session):
    """Part 26 Phase 1's "basic product performance" needs Quote lines linked to a real Product
    -- confirms that link actually gets made, not just that the schema column exists."""
    from app.core.models.product import Product

    site = _make_site(session)
    _, quote = configure_canopy_and_create_quote(
        session, site.id, width_m=6.0, length_m=4.0, roof_cover="Metal Sheet", unit_cost_per_m2=1500.0
    )
    session.commit()

    current = latest_revision(session, QuoteRevision, "quote_id", quote.id)
    linked_product = session.get(Product, current.lines[0].product_id)
    assert linked_product is not None
    assert linked_product.code == "CANOPY"


def test_quote_gate_never_shows_pass_while_the_quantity_is_a_placeholder(session):
    """C3, enforced: a placeholder-quantity quote must not look production-ready just because
    its GM% alone would clear C2's 30% pass floor -- combine_gate_statuses (Part 5) means the
    quantity-basis gate's OVERRIDE_REQUIRED can never be hidden by a passing GM%."""
    site = _make_site(session)
    # A generous unit cost pushes GM comfortably above 30% -- if C3 weren't wired in, this would
    # show as a clean PASS.
    _, quote = configure_canopy_and_create_quote(
        session, site.id, width_m=6.0, length_m=4.0, roof_cover="Metal Sheet", unit_cost_per_m2=1500.0
    )
    session.commit()

    current = latest_revision(session, QuoteRevision, "quote_id", quote.id)
    assert current.gate_status != "PASS"
    assert current.gate_status == "OVERRIDE_REQUIRED"
    assert "quantity basis" in current.gate_note.lower()


def test_configurator_derives_unit_cost_from_supplier_quotes_via_fresh_price(session):
    """Wires Sprint 1's Smart Fresh Price selection into the actual quote pipeline instead of a
    bare manual number -- a 90-day lock requirement must select the pricier-but-long-enough
    quote, exactly as app.domain.fresh_price's own tests already prove in isolation."""
    site = _make_site(session)
    quotes = [
        PriceQuote(price=1400.0, lock_days=30, source="Supplier A"),
        PriceQuote(price=1500.0, lock_days=60, source="Supplier B"),
        PriceQuote(price=1600.0, lock_days=90, source="Supplier C"),
    ]

    project, quote = configure_canopy_and_create_quote(
        session, site.id, width_m=6.0, length_m=4.0, roof_cover="Metal Sheet",
        supplier_price_quotes=quotes, required_lock_days=90,
    )
    session.commit()

    revision = latest_revision(session, ProjectRevision, "project_id", project.id)
    assert revision.data["unit_cost_per_m2"] == 1600.0  # Supplier C -- only one meeting the lock requirement

    current = latest_revision(session, QuoteRevision, "quote_id", quote.id)
    assert current.lines[0].unit_price == 1600.0


def test_configurator_rejects_both_or_neither_cost_source(session):
    site = _make_site(session)
    quotes = [PriceQuote(price=1500.0, lock_days=60, source="Supplier B")]

    with pytest.raises(ValueError):
        configure_canopy_and_create_quote(
            session, site.id, width_m=6.0, length_m=4.0, roof_cover="Metal Sheet",
        )  # neither supplied

    with pytest.raises(ValueError):
        configure_canopy_and_create_quote(
            session, site.id, width_m=6.0, length_m=4.0, roof_cover="Metal Sheet",
            unit_cost_per_m2=1500.0, supplier_price_quotes=quotes,
        )  # both supplied


def test_structural_sizing_never_appears_as_a_number_anywhere_in_the_pipeline(session):
    site = _make_site(session)
    project, _ = configure_canopy_and_create_quote(
        session, site.id, width_m=6.0, length_m=4.0, roof_cover="Metal Sheet", unit_cost_per_m2=1500.0
    )
    session.commit()

    revision = latest_revision(session, ProjectRevision, "project_id", project.id)
    assert revision.data["quantities"]["structure_sizing_status"] == "PENDING_ENGINEER_CONFIRMATION"
