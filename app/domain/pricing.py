GM30_DIVISOR = 0.70  # Selling Price = True Cost / 0.70 -- GM30 is a floor, NOT a 30% markup (C2)


def selling_price_for_gm30(true_cost: float) -> float:
    """C2: Selling Price = True Cost / 0.70, never Cost * 1.30.

    Blueprint's own worked example: Cost=100,000 -> Selling Price=142,857, Gross Profit=42,857,
    Gross Margin=30%. Cost * 1.30 would give 130,000, a gross margin of only ~23.08% -- that's
    the exact mistake this formula exists to prevent.
    """
    return true_cost / GM30_DIVISOR


def gross_margin_percent(selling_price: float, true_cost: float) -> float:
    if selling_price == 0:
        return 0.0
    return (selling_price - true_cost) / selling_price * 100
