from datetime import date

from app.core.models.party import Customer, Site
from app.core.models.product import Product
from app.core.models.project import PROJECT_STATES
from app.core.models.supplier import Supplier, SupplierQuote
from app.domain.archiving import archive
from app.domain.business_health import (
    healthy_sites_summary,
    pipeline_by_state,
    product_performance_summary,
    quote_gm_summary,
    revenue_summary,
    site_capture_summary,
    supplier_concentration_summary,
)
from app.domain.confirmations import confirm_project
from app.domain.pricing import selling_price_for_gm30
from app.domain.project_lifecycle import transition_project
from app.domain.projects import create_project
from app.domain.quotes import create_quote, update_quote
from app.domain.site_quality import flag_site


def _make_site(session, site_type="FACTORY") -> Site:
    customer = Customer(name="Acme Co")
    session.add(customer)
    session.flush()
    site = Site(customer_id=customer.id, site_type=site_type, name="Site A")
    session.add(site)
    session.flush()
    return site


def _price_for_gm(cost: float, gm_pct: float) -> float:
    return cost / (1 - gm_pct / 100)


def test_pipeline_by_state_includes_every_state_even_at_zero(session):
    counts = pipeline_by_state(session)
    assert set(counts.keys()) == set(PROJECT_STATES)
    assert all(v == 0 for v in counts.values())


def test_pipeline_by_state_counts_projects_correctly(session):
    site = _make_site(session)
    p1 = create_project(session, site.id, {})
    p2 = create_project(session, site.id, {})
    transition_project(session, p2, "QUALIFIED")
    session.commit()

    counts = pipeline_by_state(session)
    assert counts["DISCOVERED"] == 1
    assert counts["QUALIFIED"] == 1
    assert counts["SURVEYED"] == 0


def test_pipeline_by_state_excludes_archived_projects(session):
    site = _make_site(session)
    project = create_project(session, site.id, {})
    archive(session, project)
    session.commit()

    counts = pipeline_by_state(session)
    assert counts["DISCOVERED"] == 0


def test_quote_gm_summary_empty_when_no_quotes(session):
    summary = quote_gm_summary(session)
    assert summary == {"quote_count": 0, "average_gm_percent": None, "gate_status_counts": {}}


def test_quote_gm_summary_uses_current_revision_only(session):
    """A superseded revision's GM must not leak into the average -- Law 4 applied to reporting."""
    site = _make_site(session)
    project = create_project(session, site.id, {})
    cost = 100_000
    quote = create_quote(
        session, project.id, cost, selling_price_for_gm30(cost),
        [{"description": "line", "quantity": 1, "unit_price": selling_price_for_gm30(cost)}],
    )
    # Supersede it with a much worse GM -- only THIS should count, not the original 30%.
    update_quote(
        session, quote, cost, _price_for_gm(cost, 10.0),
        [{"description": "line", "quantity": 1, "unit_price": 1}],
    )
    session.commit()

    summary = quote_gm_summary(session)
    assert summary["quote_count"] == 1
    assert round(summary["average_gm_percent"], 2) == 10.0
    assert summary["gate_status_counts"] == {"BLOCKED": 1}


def test_quote_gm_summary_averages_across_multiple_quotes(session):
    site = _make_site(session)
    project_a = create_project(session, site.id, {})
    project_b = create_project(session, site.id, {})
    cost = 100_000
    create_quote(session, project_a.id, cost, _price_for_gm(cost, 30.0), [{"description": "x", "quantity": 1, "unit_price": 1}])
    create_quote(session, project_b.id, cost, _price_for_gm(cost, 20.0), [{"description": "x", "quantity": 1, "unit_price": 1}])
    session.commit()

    summary = quote_gm_summary(session)
    assert summary["quote_count"] == 2
    assert round(summary["average_gm_percent"], 2) == 25.0
    assert summary["gate_status_counts"] == {"PASS": 1, "OVERRIDE_REQUIRED": 1}


def test_site_capture_summary_counts_by_type_and_excludes_archived(session):
    factory = _make_site(session, "FACTORY")
    home = _make_site(session, "HOME")
    archived_office = _make_site(session, "OFFICE")
    archive(session, archived_office)
    session.commit()

    summary = site_capture_summary(session)
    assert summary["total_sites"] == 2
    assert summary["by_type"]["FACTORY"] == 1
    assert summary["by_type"]["HOME"] == 1
    assert summary["by_type"]["OFFICE"] == 0


def test_product_performance_summary_groups_by_product_code(session):
    site = _make_site(session)
    project = create_project(session, site.id, {})
    product = Product(code="CANOPY", name="Canopy")
    session.add(product)
    session.flush()

    create_quote(
        session, project.id, 100_000, selling_price_for_gm30(100_000),
        [{"description": "roof", "quantity": 1, "unit_price": selling_price_for_gm30(100_000), "product_id": product.id}],
    )
    session.commit()

    summary = product_performance_summary(session)
    assert summary["line_count_by_product"]["CANOPY"] == 1
    assert round(summary["revenue_by_product"]["CANOPY"], 2) == round(selling_price_for_gm30(100_000), 2)


def test_product_performance_summary_groups_unlinked_lines_separately(session):
    site = _make_site(session)
    project = create_project(session, site.id, {})
    create_quote(
        session, project.id, 100_000, selling_price_for_gm30(100_000),
        [{"description": "misc", "quantity": 1, "unit_price": selling_price_for_gm30(100_000)}],  # no product_id
    )
    session.commit()

    summary = product_performance_summary(session)
    assert summary["line_count_by_product"]["unlinked"] == 1


def test_product_performance_summary_uses_current_revision_only(session):
    site = _make_site(session)
    project = create_project(session, site.id, {})
    product = Product(code="CANOPY", name="Canopy")
    session.add(product)
    session.flush()

    quote = create_quote(
        session, project.id, 100_000, selling_price_for_gm30(100_000),
        [{"description": "v1", "quantity": 1, "unit_price": selling_price_for_gm30(100_000), "product_id": product.id}],
    )
    update_quote(
        session, quote, 100_000, selling_price_for_gm30(100_000),
        [{"description": "v2", "quantity": 1, "unit_price": 999.0, "product_id": product.id}],
    )
    session.commit()

    summary = product_performance_summary(session)
    # Only the v2 line's revenue should count -- v1 is a superseded revision (Law 4).
    assert summary["line_count_by_product"]["CANOPY"] == 1
    assert summary["revenue_by_product"]["CANOPY"] == 999.0


def test_healthy_sites_summary_counts_flagged_vs_healthy(session):
    healthy_site = _make_site(session)
    flagged_site = _make_site(session)
    flag_site(session, flagged_site.id, "BAD_PAYMENT", "Chronically late", flagged_by="PM K.")
    session.commit()

    summary = healthy_sites_summary(session)
    assert summary["total_sites"] == 2
    assert summary["healthy_sites"] == 1
    assert summary["flagged_sites"] == 1


def _confirm_a_passing_quote(session, site, project=None):
    if project is None:
        project = create_project(session, site.id, {})
    cost = 100_000
    quote = create_quote(
        session, project.id, cost, selling_price_for_gm30(cost),
        [{"description": "x", "quantity": 1, "unit_price": selling_price_for_gm30(cost)}],
    )
    return confirm_project(session, project, quote, confirmed_by="Estimator J.")


def test_revenue_summary_counts_a_customers_first_confirmation_as_new(session):
    site = _make_site(session)
    _confirm_a_passing_quote(session, site)
    session.commit()

    summary = revenue_summary(session)
    assert round(summary["new_customer_revenue"], 2) == round(selling_price_for_gm30(100_000), 2)
    assert summary["repeat_customer_revenue"] == 0.0


def test_revenue_summary_counts_a_customers_second_confirmation_as_repeat(session):
    customer = Customer(name="Repeat Customer Co")
    session.add(customer)
    session.flush()
    site_a = Site(customer_id=customer.id, site_type="FACTORY", name="Site A")
    site_b = Site(customer_id=customer.id, site_type="FACTORY", name="Site B")
    session.add_all([site_a, site_b])
    session.flush()

    _confirm_a_passing_quote(session, site_a)
    _confirm_a_passing_quote(session, site_b)  # same customer, a different site -- still repeat
    session.commit()

    summary = revenue_summary(session)
    expected_each = selling_price_for_gm30(100_000)
    assert round(summary["new_customer_revenue"], 2) == round(expected_each, 2)
    assert round(summary["repeat_customer_revenue"], 2) == round(expected_each, 2)
    assert round(summary["total_confirmed_revenue"], 2) == round(expected_each * 2, 2)


def _make_quote(session, supplier_name, material, price):
    from sqlalchemy import select

    supplier = session.execute(select(Supplier).where(Supplier.name == supplier_name)).scalar_one_or_none()
    if supplier is None:
        supplier = Supplier(name=supplier_name)
        session.add(supplier)
        session.flush()
    session.add(
        SupplierQuote(
            supplier_id=supplier.id, material_description=material, quoted_price=price,
            quote_date=date(2026, 1, 1), validity_days=14, lock_days=30, lead_time_days=21,
        )
    )


def test_supplier_concentration_summary_is_empty_with_no_supplier_data(session):
    assert supplier_concentration_summary(session) == {}


def test_supplier_concentration_summary_flags_a_single_source_material(session):
    _make_quote(session, "Supplier A", "Metal Sheet", 98.0)
    _make_quote(session, "Supplier A", "Metal Sheet", 99.0)
    _make_quote(session, "Supplier B", "Metal Sheet", 105.0)
    session.commit()

    summary = supplier_concentration_summary(session)
    assert summary["Metal Sheet"]["quote_count"] == 3
    assert summary["Metal Sheet"]["distinct_suppliers"] == 2
    assert round(summary["Metal Sheet"]["top_supplier_share_percent"], 2) == round(2 / 3 * 100, 2)


def test_supplier_concentration_summary_tracks_materials_independently(session):
    _make_quote(session, "Supplier A", "Metal Sheet", 98.0)
    _make_quote(session, "Supplier B", "Polycarbonate", 50.0)
    session.commit()

    summary = supplier_concentration_summary(session)
    assert set(summary.keys()) == {"Metal Sheet", "Polycarbonate"}
    assert summary["Metal Sheet"]["top_supplier_share_percent"] == 100.0
