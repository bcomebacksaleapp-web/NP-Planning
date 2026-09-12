"""Part 13.8: What-if Simulator. Pure re-evaluation of already-built pricing/constitution
functions under a hypothetical change -- never a new formula, just running the real GM30/gate
logic against a hypothetical input instead of the actual one. Nothing here writes to the
database; every function returns a result for the caller to inspect, matching the Blueprint's
own examples ("What if we discount 5%?", "What if material price rises 8%?").
"""

from dataclasses import dataclass

from app.domain.constitution import evaluate_gm30_gate
from app.domain.pricing import gross_margin_percent


@dataclass(frozen=True)
class WhatIfResult:
    scenario: str
    hypothetical_true_cost: float
    hypothetical_selling_price: float
    hypothetical_gm_percent: float
    gate_status: str
    gate_note: str


def simulate_cost_change(true_cost: float, selling_price: float, cost_change_percent: float) -> WhatIfResult:
    """Part 13.8 example: "What if material price rises 8%?" Positive = cost increase, negative
    = cost decrease."""
    new_cost = true_cost * (1 + cost_change_percent / 100)
    gm_percent = gross_margin_percent(selling_price, new_cost)
    status, note = evaluate_gm30_gate(gm_percent)
    return WhatIfResult(
        scenario=f"cost change {cost_change_percent:+.1f}%",
        hypothetical_true_cost=new_cost,
        hypothetical_selling_price=selling_price,
        hypothetical_gm_percent=gm_percent,
        gate_status=status,
        gate_note=note,
    )


def simulate_discount(true_cost: float, selling_price: float, discount_percent: float) -> WhatIfResult:
    """Part 13.8 example: "What if we discount 5%?" """
    new_price = selling_price * (1 - discount_percent / 100)
    gm_percent = gross_margin_percent(new_price, true_cost)
    status, note = evaluate_gm30_gate(gm_percent)
    return WhatIfResult(
        scenario=f"discount {discount_percent:.1f}%",
        hypothetical_true_cost=true_cost,
        hypothetical_selling_price=new_price,
        hypothetical_gm_percent=gm_percent,
        gate_status=status,
        gate_note=note,
    )
