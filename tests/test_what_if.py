from app.domain.pricing import selling_price_for_gm30
from app.domain.what_if import simulate_cost_change, simulate_discount


def test_simulate_cost_change_matches_the_blueprints_own_example():
    """Part 13.8: "What if material price rises 8%?" A canopy at exactly 30% GM, with steel
    cost +8%, should drop below the 30% pass floor."""
    true_cost = 100_000
    selling_price = selling_price_for_gm30(true_cost)  # exactly 30% GM today

    result = simulate_cost_change(true_cost, selling_price, cost_change_percent=8.0)

    assert result.hypothetical_true_cost == 108_000
    assert result.hypothetical_selling_price == selling_price  # price itself is untouched
    assert result.hypothetical_gm_percent < 30.0
    assert result.gate_status != "PASS"


def test_simulate_cost_change_with_a_decrease_improves_margin():
    true_cost = 100_000
    selling_price = selling_price_for_gm30(true_cost)

    result = simulate_cost_change(true_cost, selling_price, cost_change_percent=-10.0)

    assert result.hypothetical_true_cost == 90_000
    assert result.hypothetical_gm_percent > 30.0
    assert result.gate_status == "PASS"


def test_simulate_discount_matches_the_blueprints_own_example():
    """Part 13.8: "What if we discount 5%?" """
    true_cost = 100_000
    selling_price = selling_price_for_gm30(true_cost)

    result = simulate_discount(true_cost, selling_price, discount_percent=5.0)

    assert result.hypothetical_selling_price == selling_price * 0.95
    assert result.hypothetical_true_cost == true_cost  # cost itself is untouched
    assert result.hypothetical_gm_percent < 30.0
    assert result.gate_status != "PASS"


def test_simulations_do_not_mutate_their_inputs():
    """Pure functions -- nothing about this should look like a real recorded decision."""
    true_cost = 100_000
    selling_price = selling_price_for_gm30(true_cost)

    simulate_discount(true_cost, selling_price, discount_percent=20.0)

    assert true_cost == 100_000
    assert selling_price == selling_price_for_gm30(100_000)
