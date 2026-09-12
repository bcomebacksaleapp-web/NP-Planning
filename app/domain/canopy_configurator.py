import uuid

from sqlalchemy.orm import Session

from app.core.models.project import Project
from app.core.models.quote import Quote
from app.domain.canopy_recipe import compute_canopy_quantities
from app.domain.pricing import selling_price_for_gm30
from app.domain.projects import create_project
from app.domain.quotes import create_quote


def configure_canopy_and_create_quote(
    session: Session,
    site_id: uuid.UUID,
    width_m: float,
    length_m: float,
    roof_cover: str,
    unit_cost_per_m2: float,
    actor_user_id: uuid.UUID | None = None,
) -> tuple[Project, Quote]:
    """Customer Mode's minimal configurator flow (Part 12), proving Phase 1's own acceptance
    criterion directly: "Customer configuration must generate canonical business data, not
    UI-only data." Every call creates real Project/ProjectRevision/Quote/QuoteRevision/QuoteLine
    rows -- see tests/test_canopy_configurator.py, which checks the database, not just this
    function's return value.

    `unit_cost_per_m2` is a required, explicit input -- there is no real supplier cost data to
    derive it from yet (app.domain.suppliers exists but is unpopulated), so this function does
    not invent one. Quantities come from app.domain.canopy_recipe's PLACEHOLDER geometry
    formulas -- read that module's warning before trusting these numbers for a real quote.
    """
    quantities = compute_canopy_quantities(width_m, length_m)

    project = create_project(
        session,
        site_id,
        data={
            "product": "CANOPY",
            "width_m": width_m,
            "length_m": length_m,
            "roof_cover": roof_cover,
            "quantities": quantities,
        },
        actor_user_id=actor_user_id,
    )

    true_cost = quantities["roof_area_m2_with_waste"] * unit_cost_per_m2
    selling_price = selling_price_for_gm30(true_cost)
    quote = create_quote(
        session,
        project.id,
        true_cost=true_cost,
        selling_price=selling_price,
        lines=[
            {
                "description": f"Canopy roof ({roof_cover}), {width_m}m x {length_m}m",
                "quantity": quantities["roof_area_m2_with_waste"],
                "unit_price": unit_cost_per_m2,
            }
        ],
        actor_user_id=actor_user_id,
    )
    return project, quote
