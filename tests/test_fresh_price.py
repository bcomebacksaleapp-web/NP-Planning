import pytest

from app.domain.fresh_price import (
    PriceQuote,
    market_reference_price,
    needs_dispersion_investigation,
    select_procurement_quote,
)


def test_market_reference_uses_median_not_average():
    """Part 17's own example: A=98, B=101, C=105 -> median market reference = 101."""
    quotes = [PriceQuote(98, 30, "A"), PriceQuote(101, 60, "B"), PriceQuote(105, 90, "C")]
    assert market_reference_price(quotes) == 101


def test_market_reference_raises_on_no_quotes():
    with pytest.raises(ValueError):
        market_reference_price([])


def test_select_procurement_quote_respects_required_lock_duration():
    """Part 17: customer requires 90-day lock -> selected procurement cost is 105, not the
    cheaper 98/101 quotes that don't lock long enough."""
    quotes = [PriceQuote(98, 30, "A"), PriceQuote(101, 60, "B"), PriceQuote(105, 90, "C")]
    selected = select_procurement_quote(quotes, required_lock_days=90)
    assert selected.source == "C"
    assert selected.price == 105


def test_select_procurement_quote_picks_cheapest_eligible_quote():
    quotes = [PriceQuote(98, 30, "A"), PriceQuote(101, 60, "B"), PriceQuote(105, 90, "C")]
    selected = select_procurement_quote(quotes, required_lock_days=30)
    assert selected.source == "A"
    assert selected.price == 98


def test_select_procurement_quote_raises_when_nothing_meets_the_lock_requirement():
    quotes = [PriceQuote(98, 30), PriceQuote(101, 60)]
    with pytest.raises(ValueError):
        select_procurement_quote(quotes, required_lock_days=90)


def test_dispersion_does_not_flag_the_blueprints_normal_example():
    """98 / 101 / 105 must NOT trigger investigation."""
    quotes = [PriceQuote(98, 30), PriceQuote(101, 60), PriceQuote(105, 90)]
    assert needs_dispersion_investigation(quotes) is False


def test_dispersion_flags_the_blueprints_own_investigation_example():
    """98 / 101 / 145 MUST trigger investigation, not automatic averaging."""
    quotes = [PriceQuote(98, 30), PriceQuote(101, 60), PriceQuote(145, 90)]
    assert needs_dispersion_investigation(quotes) is True


def test_dispersion_is_zero_with_fewer_than_two_quotes():
    assert needs_dispersion_investigation([PriceQuote(100, 30)]) is False
    assert needs_dispersion_investigation([]) is False
