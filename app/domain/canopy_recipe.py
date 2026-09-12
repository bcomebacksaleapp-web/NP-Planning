"""EXAMPLE/PLACEHOLDER canopy quantity takeoff -- NOT a verified business formula.

Exists to prove the Customer-configuration -> canonical-data pipeline end-to-end (Blueprint
Phase 1 acceptance: "Customer configuration must generate canonical business data, not UI-only
data"), using generic, illustrative geometry math and a round, unsourced waste-factor number.
None of it has been verified against the business's real takeoff methodology, a real supplier
quote, or a real project. A filesystem search across every other project on this machine (see
git log / conversation history) found no existing canopy BOQ formula to use instead.

Replace PLACEHOLDER_WASTE_FACTOR_PERCENT and the gutter/flashing conventions below with the
business's actual numbers before using this for a single real quote.

Structural member sizing (column/beam/rafter) is deliberately NEVER computed here, placeholder
or not. Part 22 requires a qualified engineer to determine that from geometry + load, and Law 13
(safety/engineering truth has the highest priority) is not something a "just for testing" label
gets to override. structure_sizing_status below is always "PENDING_ENGINEER_CONFIRMATION",
never a number -- that boundary does not relax just because the rest of this module is a
placeholder.
"""

FORMULA_STATUS = "UNVERIFIED_PLACEHOLDER"

# Generic, illustrative -- not sourced from any real project, supplier, or business record.
PLACEHOLDER_WASTE_FACTOR_PERCENT = 5.0


def placeholder_canopy_recipe_formula() -> dict:
    """The RecipeVersion.formula payload for a placeholder Canopy recipe. Documents its own
    unverified status inside the stored data itself, not only in this module's docstring, so
    the warning survives being read out of the database later with this file not open."""
    return {
        "status": FORMULA_STATUS,
        "warning": (
            "Generic example formula for pipeline testing only. NOT calibrated to real "
            "business data. Must be replaced with the business's actual takeoff methodology "
            "before any real quote is issued."
        ),
        "geometry": {
            "roof_area_m2": "width_m * length_m",
            "gutter_length_m": "length_m (illustrative: gutter along one long eave, unverified convention)",
            "flashing_length_m": "2 * width_m (illustrative: flashing along both short edges, unverified convention)",
        },
        "waste_factor_percent": PLACEHOLDER_WASTE_FACTOR_PERCENT,
        "structure_sizing_status": "PENDING_ENGINEER_CONFIRMATION",
        "structure_sizing_note": (
            "Column/beam/rafter sizing must be determined by a qualified engineer from "
            "geometry and load (Part 22) -- never calculated or guessed by this system, "
            "placeholder or not."
        ),
    }


def compute_canopy_quantities(width_m: float, length_m: float) -> dict:
    """Applies the placeholder geometry formulas above to real customer-entered dimensions.

    Pure geometry (area, perimeter-derived lengths from two positive numbers) is safe generic
    math. The waste factor and the choice of which edge the gutter/flashing runs along are the
    unverified, illustrative parts -- see module docstring.
    """
    if width_m <= 0 or length_m <= 0:
        raise ValueError("width_m and length_m must be positive")

    roof_area_m2 = width_m * length_m
    waste_multiplier = 1 + PLACEHOLDER_WASTE_FACTOR_PERCENT / 100

    return {
        "roof_area_m2": roof_area_m2,
        "roof_area_m2_with_waste": roof_area_m2 * waste_multiplier,
        "gutter_length_m": length_m,
        "flashing_length_m": 2 * width_m,
        "structure_sizing_status": "PENDING_ENGINEER_CONFIRMATION",
        "formula_status": FORMULA_STATUS,
    }
