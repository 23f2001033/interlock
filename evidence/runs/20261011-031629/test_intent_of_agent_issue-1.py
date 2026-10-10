"""Test that money is represented as integer cents end-to-end."""

from shop.cart import Cart
from shop.money import format_money
from shop.orders import place_order
from shop.payments import PaymentGateway
from shop.pricing import quote


def test_all_amounts_are_integer_cents():
    """Verify that catalog prices, cart subtotal, shipping, tax, and order totals are all int cents."""
    cart = Cart()
    cart.add("TEE-01", 2)
    cart.add("BAG-01", 1)
    
    # Cart subtotal is int cents
    subtotal = cart.subtotal()
    assert isinstance(subtotal, int)
    assert subtotal == 3998 + 995  # 2 * 1999 + 995
    
    # Quote breakdown is all int cents
    q = quote(cart, "US-CA")
    assert all(isinstance(v, int) for v in q.values())
    assert q["subtotal"] == 4993
    assert q["shipping"] == 500
    assert q["tax"] == 362  # 4993 * 0.0725 = 362.0425, rounded to 362
    assert q["total"] == 5855
    
    # Order amounts are int cents
    gateway = PaymentGateway()
    order = place_order(cart, "cus_1", "US-CA", gateway)
    assert isinstance(order.subtotal, int)
    assert isinstance(order.shipping, int)
    assert isinstance(order.tax, int)
    assert isinstance(order.total, int)
    assert order.total == 5855
    
    # Payment gateway receives int cents
    assert gateway.charges[0].amount_cents == 5855
    assert isinstance(gateway.charges[0].amount_cents, int)


def test_no_one_cent_mismatches_with_tax_rounding():
    """Verify that tax rounding to nearest cent doesn't cause mismatches."""
    cart = Cart()
    cart.add("TEE-01", 1)  # 1999 cents
    
    q = quote(cart, "US-CA")
    # 1999 * 0.0725 = 144.9275, rounds to 145
    assert q["tax"] == 145
    
    # Total should be exact: subtotal + shipping + tax
    assert q["total"] == q["subtotal"] + q["shipping"] + q["tax"]
    
    gateway = PaymentGateway()
    order = place_order(cart, "cus_1", "US-CA", gateway)
    
    # Order total matches what was charged
    assert order.total == gateway.charges[0].amount_cents


def test_format_money_displays_cents_as_dollars():
    """Verify that integer cents are correctly formatted for display."""
    assert format_money(0) == "$0.00"
    assert format_money(1999) == "$19.99"
    assert format_money(123450) == "$1,234.50"
    assert format_money(500) == "$5.00"
    assert format_money(5) == "$0.05"
