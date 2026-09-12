GATE_PASS = "PASS"
GATE_OVERRIDE_REQUIRED = "OVERRIDE_REQUIRED"
GATE_BLOCKED = "BLOCKED"

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
