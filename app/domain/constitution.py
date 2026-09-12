GATE_PASS = "PASS"
GATE_WARNING = "WARNING"
GATE_OVERRIDE_REQUIRED = "OVERRIDE_REQUIRED"
GATE_BLOCKED = "BLOCKED"
_STATUS_SEVERITY = {GATE_PASS: 0, GATE_WARNING: 1, GATE_OVERRIDE_REQUIRED: 2, GATE_BLOCKED: 3}

# C2 initial policy, verbatim from the Blueprint. "Initial" because the Blueprint itself frames
# these as a starting point management can tune -- not a claim that these exact cutoffs are
# permanent. Changing them is a business decision, not something to silently adjust here.
_MANAGEMENT_OVERRIDE_FLOOR = 27.0
_SENIOR_OVERRIDE_FLOOR = 20.0
_PASS_FLOOR = 30.0


def evaluate_gm30_gate(gross_margin_pct: float) -> tuple[str, str]:
    """>=30% pass, 27-29.99% management override, 20-26.99% senior override / strategic
    investment, <20% default block.

    A high score elsewhere can never compensate for this: a hard block from this gate is not
    something a weighted composite score should be allowed to override (Part 5's "a high score
    cannot compensate for a hard block" -- this function doesn't enforce that composition rule
    itself, but callers combining this with other gates must not average it away).
    """
    if gross_margin_pct >= _PASS_FLOOR:
        return GATE_PASS, ""
    if gross_margin_pct >= _MANAGEMENT_OVERRIDE_FLOOR:
        return GATE_OVERRIDE_REQUIRED, f"management override required (GM {gross_margin_pct:.2f}%, 27.00-29.99% band)"
    if gross_margin_pct >= _SENIOR_OVERRIDE_FLOOR:
        return (
            GATE_OVERRIDE_REQUIRED,
            f"senior override / strategic investment required (GM {gross_margin_pct:.2f}%, 20.00-26.99% band)",
        )
    return GATE_BLOCKED, f"blocked by default (GM {gross_margin_pct:.2f}%, below 20% floor)"


def evaluate_stale_cost_gate(stale_exposure_pct: float) -> tuple[str, str]:
    """C1, verbatim: stale exposure = Stale Cost / Total Relevant Cost. <2% = warning,
    2-10% = management override, >10% = block.

    Unlike the other gates here, the Blueprint's own initial policy for C1 never returns PASS --
    any non-zero stale exposure warrants at least a warning. That's the Blueprint's own text as
    written, not an omission: if a clean pass state at exactly 0% is wanted, that's a policy
    decision to make explicitly, not to infer silently (Law 9).
    """
    if stale_exposure_pct > 10:
        return GATE_BLOCKED, f"blocked: stale cost exposure {stale_exposure_pct:.2f}% exceeds 10%"
    if stale_exposure_pct >= 2:
        return (
            GATE_OVERRIDE_REQUIRED,
            f"management override required: stale cost exposure {stale_exposure_pct:.2f}% (2-10% band)",
        )
    return GATE_WARNING, f"warning: stale cost exposure {stale_exposure_pct:.2f}% (below 2%)"


def evaluate_price_lock_gate(coverage_pct: float) -> tuple[str, str]:
    """C6, verbatim: Lock Coverage = Secured Price-Sensitive Cost / Total Price-Sensitive Cost.
    >=95% pass, 80-94.9% warning, 50-79.9% override, <50% block unless explicit mitigation."""
    if coverage_pct >= 95:
        return GATE_PASS, ""
    if coverage_pct >= 80:
        return GATE_WARNING, f"warning: price lock coverage {coverage_pct:.2f}% (80-94.9% band)"
    if coverage_pct >= 50:
        return GATE_OVERRIDE_REQUIRED, f"override required: price lock coverage {coverage_pct:.2f}% (50-79.9% band)"
    return GATE_BLOCKED, f"blocked unless explicit mitigation: price lock coverage {coverage_pct:.2f}% (below 50%)"


CAPACITY_UNDERUTILIZED = "UNDERUTILIZED"
CAPACITY_HEALTHY = "HEALTHY"
CAPACITY_WARNING = "WARNING"
CAPACITY_OVERRIDE_REQUIRED = "OVERRIDE_REQUIRED"
CAPACITY_BLOCKED = "BLOCKED"


def evaluate_capacity_gate(utilization_pct: float) -> tuple[str, str]:
    """C9, verbatim bands: <60% underutilized, 60-85% healthy, 85-95% warning, 95-105% override,
    >105% block unless approved capacity plan.

    Unlike C1/C2/C6, capacity has a floor as well as a ceiling -- underutilized is its own
    distinct status, not folded into "pass", since being underused is also a real problem the
    Blueprint wants surfaced (Part 14: "are we underloaded or overloaded?").
    """
    if utilization_pct > 105:
        return CAPACITY_BLOCKED, f"blocked unless approved capacity plan: utilization {utilization_pct:.2f}% (above 105%)"
    if utilization_pct >= 95:
        return CAPACITY_OVERRIDE_REQUIRED, f"override required: utilization {utilization_pct:.2f}% (95-105% band)"
    if utilization_pct >= 85:
        return CAPACITY_WARNING, f"warning: utilization {utilization_pct:.2f}% (85-95% band)"
    if utilization_pct >= 60:
        return CAPACITY_HEALTHY, f"healthy: utilization {utilization_pct:.2f}% (60-85% band)"
    return CAPACITY_UNDERUTILIZED, f"underutilized: utilization {utilization_pct:.2f}% (below 60%)"


def combine_gate_statuses(statuses: list[str]) -> str:
    """Part 5: "a high score cannot compensate for a hard block." The actual enforcement of that
    rule -- any BLOCKED anywhere makes the combined result BLOCKED regardless of how many other
    gates PASS; any OVERRIDE_REQUIRED (with nothing worse) makes it OVERRIDE_REQUIRED; only if
    every gate PASSes (or WARNs) does the combination reflect that.

    Only meaningful for gates using the PASS/WARNING/OVERRIDE_REQUIRED/BLOCKED vocabulary
    (C1/C2/C6) -- capacity's UNDERUTILIZED/HEALTHY/... vocabulary is deliberately not comparable
    with this, since "underutilized" isn't a severity ranking against the others.
    """
    if not statuses:
        raise ValueError("No gate statuses to combine")
    return max(statuses, key=lambda status: _STATUS_SEVERITY[status])
