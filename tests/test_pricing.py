from app.domain.constitution import GATE_BLOCKED, GATE_OVERRIDE_REQUIRED, GATE_PASS, evaluate_gm30_gate
from app.domain.pricing import gross_margin_percent, selling_price_for_gm30


def test_selling_price_matches_the_blueprints_own_worked_example():
    selling_price = selling_price_for_gm30(100_000)
    assert round(selling_price) == 142_857

    gross_profit = selling_price - 100_000
    assert round(gross_profit) == 42_857

    gm = gross_margin_percent(selling_price, 100_000)
    assert round(gm, 2) == 30.00


def test_cost_times_1_3_is_the_wrong_formula_and_produces_a_lower_margin():
    """C2 explicitly forbids Cost * 1.30 -- confirms it's not just a stylistic preference, it
    actually produces a different (lower) margin than the required 30%."""
    correct_price = selling_price_for_gm30(100_000)
    wrong_markup_price = 100_000 * 1.30

    assert correct_price != wrong_markup_price
    assert round(gross_margin_percent(wrong_markup_price, 100_000), 2) == 23.08  # not 30%


def test_gate_pass_at_and_above_30_percent():
    assert evaluate_gm30_gate(30.0)[0] == GATE_PASS
    assert evaluate_gm30_gate(35.0)[0] == GATE_PASS


def test_gate_management_override_band():
    assert evaluate_gm30_gate(29.99)[0] == GATE_OVERRIDE_REQUIRED
    assert evaluate_gm30_gate(27.0)[0] == GATE_OVERRIDE_REQUIRED
    assert "management" in evaluate_gm30_gate(28.5)[1].lower()


def test_gate_senior_override_band():
    assert evaluate_gm30_gate(26.99)[0] == GATE_OVERRIDE_REQUIRED
    assert evaluate_gm30_gate(20.0)[0] == GATE_OVERRIDE_REQUIRED
    assert "senior" in evaluate_gm30_gate(22.0)[1].lower()


def test_gate_blocked_below_20_percent():
    assert evaluate_gm30_gate(19.99)[0] == GATE_BLOCKED
    assert evaluate_gm30_gate(0.0)[0] == GATE_BLOCKED
    assert evaluate_gm30_gate(-10.0)[0] == GATE_BLOCKED  # negative GM (selling below cost)
