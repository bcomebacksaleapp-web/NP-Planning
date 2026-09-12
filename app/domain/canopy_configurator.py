import uuid

from sqlalchemy.orm import Session

from app.core.models.project import Project
from app.core.models.quote import Quote
from app.domain.canopy_recipe import compute_canopy_quantities
from app.domain.constitution import evaluate_quantity_basis_gate
from app.domain.fresh_price import PriceQuote, select_procurement_quote
from app.domain.pricing import selling_price_for_gm30
from app.domain.projects import create_project
from app.domain.quotes import create_quote
from app.domain.recipes import get_or_create_product

CANOPY_PRODUCT_CODE = "CANOPY"


def configure_canopy_and_create_quote(
    session: Session,
    site_id: uuid.UUID,
    width_m: float,
    length_m: float,
    roof_cover: str,
    unit_cost_per_m2: float | None = None,
    supplier_price_quotes: list[PriceQuote] | None = None,
    required_lock_days: int = 0,
    actor_user_id: uuid.UUID | None = None,
) -> tuple[Project, Quote]:
    """Customer Mode's minimal configurator flow (Part 12), proving Phase 1's own acceptance
    criterion directly: "Customer configuration must generate canonical business data, not
    UI-only data." Every call creates real Project/ProjectRevision/Quote/QuoteRevision/QuoteLine
    rows -- see tests/test_canopy_configurator.py, which checks the database, not just this
    function's return value.

    Cost comes from exactly one of two places, never both:
    - `unit_cost_per_m2`, a manual number you supply directly, or
    - `supplier_price_quotes` + `required_lock_days`, run through Sprint 1's Smart Fresh Price
      selection (median-aware, lock-duration-respecting -- app.domain.fresh_price), the same
      logic app.domain.suppliers.to_price_quote feeds real SupplierQuote rows into.

    Neither path invents a price -- there is still no real supplier data populated anywhere, so
    in practice this is exercised with explicitly-synthetic PriceQuote objects in tests, the same
    way every other test in this repo uses made-up-but-labeled-as-test numbers to prove code
    works, not to assert real business truth.

    Quantities come from app.domain.canopy_recipe's PLACEHOLDER geometry formulas -- read that
    module's warning before trusting these numbers for a real quote.
    """
    if (unit_cost_per_m2 is None) == (not supplier_price_quotes):
        raise ValueError("Supply exactly one of unit_cost_per_m2 or supplier_price_quotes")

    if supplier_price_quotes:
        selected = select_procurement_quote(supplier_price_quotes, required_lock_days)
        unit_cost_per_m2 = selected.price

    quantities = compute_canopy_quantities(width_m, length_m)
    product = get_or_create_product(session, CANOPY_PRODUCT_CODE, "Canopy")

    project = create_project(
        session,
        site_id,
        data={
            "product": "CANOPY",
            "width_m": width_m,
            "length_m": length_m,
            "roof_cover": roof_cover,
            "quantities": quantities,
            "unit_cost_per_m2": unit_cost_per_m2,
        },
        actor_user_id=actor_user_id,
    )

    true_cost = quantities["roof_area_m2_with_waste"] * unit_cost_per_m2
    selling_price = selling_price_for_gm30(true_cost)
    # selling_price_for_gm30 is a linear scaling (divide by 0.70), so applying it per unit and
    # multiplying by quantity gives exactly the same total as applying it once to the aggregate
    # true_cost above -- this is what actually gets charged per m2, not the raw cost. QuoteLine's
    # unit_price must be the selling price, never cost (see QuoteLine's docstring for why: this
    # line used to pass unit_cost_per_m2 straight through, which made product_performance_summary
    # silently report cost as "revenue").
    unit_selling_price_per_m2 = selling_price_for_gm30(unit_cost_per_m2)
    # C3: this quote's quantity comes from an UNVERIFIED_PLACEHOLDER formula (see
    # canopy_recipe.py) -- folding that into the quote's gate via combine_gate_statuses means it
    # can never show as a clean PASS just because the GM% alone happens to clear 30%.
    quantity_gate = evaluate_quantity_basis_gate(quantities["formula_status"])
    quote = create_quote(
        session,
        project.id,
        true_cost=true_cost,
        selling_price=selling_price,
        lines=[
            {
                "description": f"Canopy roof ({roof_cover}), {width_m}m x {length_m}m",
                "quantity": quantities["roof_area_m2_with_waste"],
                "unit_price": unit_selling_price_per_m2,
                "product_id": product.id,
            }
        ],
        actor_user_id=actor_user_id,
        additional_gates=[quantity_gate],
    )
    return project, quote
