"""Smart Fresh Price (Part 17). This module trusts that "qualified" already happened -- correct
spec, actual availability, acceptable quality, deliverable, fresh quote, acceptable commercial
terms -- it doesn't re-validate any of that, only combines already-qualified quotes.
"""

from dataclasses import dataclass
from statistics import median


@dataclass(frozen=True)
class PriceQuote:
    price: float
    lock_days: int
    source: str = ""


# Part 17's own dispersion example: 98/101/105 (spread ~6.9% of the median) must NOT trigger
# investigation, but 98/101/145 (spread ~46.5%) MUST. 20% is just large enough to separate those
# two cases as the Blueprint describes them -- not a precisely business-calibrated number, and
# management should feel free to tune it once real dispersion patterns are observed.
DISPERSION_THRESHOLD_PERCENT = 20.0


def market_reference_price(quotes: list[PriceQuote]) -> float:
    """Median across qualified sources. Part 17 explicitly forbids blind averaging -- a single
    outlier quote should not drag a median-based reference the way it would a mean."""
    if not quotes:
        raise ValueError("No qualified price quotes to reference")
    return median(q.price for q in quotes)


def price_dispersion_percent(quotes: list[PriceQuote]) -> float:
    """(max - min) / median * 100 -- how spread out the qualified quotes are."""
    if len(quotes) < 2:
        return 0.0
    prices = [q.price for q in quotes]
    reference = median(prices)
    if reference == 0:
        return 0.0
    return (max(prices) - min(prices)) / reference * 100


def needs_dispersion_investigation(quotes: list[PriceQuote]) -> bool:
    return price_dispersion_percent(quotes) > DISPERSION_THRESHOLD_PERCENT


def select_procurement_quote(quotes: list[PriceQuote], required_lock_days: int) -> PriceQuote:
    """Committed/selected procurement cost, distinct from the market reference (Part 17): the
    selected quote must actually satisfy the required lock duration -- the Blueprint's own
    example has a 90-day requirement select the 105 quote over the cheaper 98/101 ones, because
    those don't lock long enough.

    Among quotes that do satisfy the requirement, picks the cheapest. Lead time / MOQ /
    reliability trade-offs among otherwise-eligible quotes are real business judgment calls this
    function deliberately does not make.
    """
    eligible = [q for q in quotes if q.lock_days >= required_lock_days]
    if not eligible:
        raise ValueError(f"No quote offers a lock period >= {required_lock_days} days")
    return min(eligible, key=lambda q: q.price)
