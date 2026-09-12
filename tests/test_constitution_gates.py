from app.domain.constitution import (
    CAPACITY_BLOCKED,
    CAPACITY_HEALTHY,
    CAPACITY_OVERRIDE_REQUIRED,
    CAPACITY_UNDERUTILIZED,
    CAPACITY_WARNING,
    GATE_BLOCKED,
    GATE_OVERRIDE_REQUIRED,
    GATE_PASS,
    GATE_WARNING,
    QUANTITY_BASIS_VERIFIED,
    combine_gate_statuses,
    evaluate_capacity_gate,
    evaluate_price_lock_gate,
    evaluate_quantity_basis_gate,
    evaluate_stale_cost_gate,
)


def test_stale_cost_gate_boundaries():
    assert evaluate_stale_cost_gate(1.99)[0] == GATE_WARNING
    assert evaluate_stale_cost_gate(2.0)[0] == GATE_OVERRIDE_REQUIRED
    assert evaluate_stale_cost_gate(10.0)[0] == GATE_OVERRIDE_REQUIRED
    assert evaluate_stale_cost_gate(10.01)[0] == GATE_BLOCKED
    assert evaluate_stale_cost_gate(0.0)[0] == GATE_WARNING  # C1 never returns PASS, per the text


def test_price_lock_gate_boundaries():
    assert evaluate_price_lock_gate(95.0)[0] == GATE_PASS
    assert evaluate_price_lock_gate(94.9)[0] == GATE_WARNING
    assert evaluate_price_lock_gate(80.0)[0] == GATE_WARNING
    assert evaluate_price_lock_gate(79.9)[0] == GATE_OVERRIDE_REQUIRED
    assert evaluate_price_lock_gate(50.0)[0] == GATE_OVERRIDE_REQUIRED
    assert evaluate_price_lock_gate(49.9)[0] == GATE_BLOCKED


def test_capacity_gate_boundaries():
    assert evaluate_capacity_gate(59.9)[0] == CAPACITY_UNDERUTILIZED
    assert evaluate_capacity_gate(60.0)[0] == CAPACITY_HEALTHY
    assert evaluate_capacity_gate(84.9)[0] == CAPACITY_HEALTHY
    assert evaluate_capacity_gate(85.0)[0] == CAPACITY_WARNING
    assert evaluate_capacity_gate(94.9)[0] == CAPACITY_WARNING
    assert evaluate_capacity_gate(95.0)[0] == CAPACITY_OVERRIDE_REQUIRED
    assert evaluate_capacity_gate(105.0)[0] == CAPACITY_OVERRIDE_REQUIRED
    assert evaluate_capacity_gate(105.01)[0] == CAPACITY_BLOCKED


def test_quantity_basis_gate_passes_only_when_verified():
    assert evaluate_quantity_basis_gate(QUANTITY_BASIS_VERIFIED)[0] == GATE_PASS


def test_quantity_basis_gate_requires_override_for_any_unverified_status():
    status, note = evaluate_quantity_basis_gate("UNVERIFIED_PLACEHOLDER")
    assert status == GATE_OVERRIDE_REQUIRED
    assert "UNVERIFIED_PLACEHOLDER" in note


def test_combine_gate_statuses_a_block_always_wins():
    """Part 5: a high score cannot compensate for a hard block."""
    assert combine_gate_statuses([GATE_PASS, GATE_PASS, GATE_BLOCKED]) == GATE_BLOCKED


def test_combine_gate_statuses_override_beats_warning_and_pass():
    assert combine_gate_statuses([GATE_PASS, GATE_WARNING, GATE_OVERRIDE_REQUIRED]) == GATE_OVERRIDE_REQUIRED


def test_combine_gate_statuses_all_pass_is_pass():
    assert combine_gate_statuses([GATE_PASS, GATE_PASS]) == GATE_PASS


def test_combine_gate_statuses_raises_on_empty_list():
    import pytest

    with pytest.raises(ValueError):
        combine_gate_statuses([])
