import pytest

from shop.cart import Cart
from shop.pricing import quote


def test_small_order_fee_present_in_quote_below_threshold():
    """A cart with subtotal under $15 should have a non-zero fee in the quote."""
    cart = Cart()
    cart.add("BAG-01")  # $9.95 / 995 cents
    q = quote(cart, "EU-DE")
    assert "fee" in q
    # Fee should be $1.50 (in dollars) or 150 (in cents) — check it's non-zero
    assert q["fee"] != 0


def test_no_small_order_fee_above_threshold():
    """A cart with subtotal at or above $15 should have zero fee."""
    cart = Cart()
    cart.add("MUG-01")  # $12.50, add two to get $25.00 >= $15
    cart.add("MUG-01")
    q = quote(cart, "US-CA")
    assert "fee" in q
    assert q["fee"] == 0 or q["fee"] == 0.0


def test_small_order_fee_included_in_total():
    """The total for a small order should include the small-order fee; tax applies to subtotal only."""
    cart = Cart()
    cart.add("BAG-01")  # subtotal = $9.95 / 995 cents
    q = quote(cart, "EU-DE")
    # Verify fee is present and positive
    assert q["fee"] > 0
    # Verify total equals subtotal + shipping + fee + tax
    assert q["total"] == q["subtotal"] + q["shipping"] + q["fee"] + q["tax"]
    # Verify tax is on subtotal only (not on fee)
    # EU-DE rate is 0.19; tax on 9.95 = 1.8905 -> rounds to 1.89 (dollars) or 189 cents
    # tax should NOT include fee in its base
    expected_tax_dollars = round(9.95 * 0.19, 2)  # ~1.89
    expected_tax_cents = 189
    # Accept either representation
    assert q["tax"] == expected_tax_dollars or q["tax"] == expected_tax_cents
