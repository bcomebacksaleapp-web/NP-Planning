import pytest

from app.domain.canopy_recipe import (
    FORMULA_STATUS,
    PLACEHOLDER_WASTE_FACTOR_PERCENT,
    compute_canopy_quantities,
    placeholder_canopy_recipe_formula,
)


def test_formula_declares_its_own_unverified_status_in_the_data():
    """The warning must survive being read out of the database later -- not just live in this
    module's docstring."""
    formula = placeholder_canopy_recipe_formula()
    assert formula["status"] == "UNVERIFIED_PLACEHOLDER"
    assert "not calibrated to real business data" in formula["warning"].lower()


def test_formula_never_computes_structural_sizing():
    formula = placeholder_canopy_recipe_formula()
    assert formula["structure_sizing_status"] == "PENDING_ENGINEER_CONFIRMATION"


def test_compute_quantities_applies_documented_geometry_and_waste_factor():
    result = compute_canopy_quantities(width_m=6.0, length_m=4.0)
    assert result["roof_area_m2"] == 24.0
    assert result["roof_area_m2_with_waste"] == 24.0 * (1 + PLACEHOLDER_WASTE_FACTOR_PERCENT / 100)
    assert result["gutter_length_m"] == 4.0
    assert result["flashing_length_m"] == 12.0
    assert result["formula_status"] == FORMULA_STATUS


def test_compute_quantities_never_computes_structural_sizing_either():
    """Same guarantee as the recipe formula itself -- computing real numbers from real customer
    dimensions must not quietly start including a structural value."""
    result = compute_canopy_quantities(width_m=6.0, length_m=4.0)
    assert result["structure_sizing_status"] == "PENDING_ENGINEER_CONFIRMATION"


def test_compute_quantities_rejects_non_positive_dimensions():
    with pytest.raises(ValueError):
        compute_canopy_quantities(width_m=0, length_m=4.0)
    with pytest.raises(ValueError):
        compute_canopy_quantities(width_m=6.0, length_m=-1.0)
