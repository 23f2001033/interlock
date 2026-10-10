"""Tests for Change X: integer cents representation end-to-end."""

import pytest

from shop.cart import Cart
from shop.catalog import price_of
from shop.money import format_money, apply_rate
from shop.payments import PaymentGateway
from shop.orders import place_order


def test_catalog_prices_and_cart_subtotal_are_integer_cents():
    # Catalog prices must be int cents
    assert price_of("MUG-01") == 1250
    assert price_of("TEE-01") == 1999
    assert price_of("CAP-01") == 1500
    assert price_of("BAG-01") == 995
    assert type(price_of("MUG-01")) is int

    # Cart subtotal must be int cents
    cart = Cart()
    cart.add("TEE-01", 2)
    assert cart.subtotal() == 3998
    assert type(cart.subtotal()) is int

    cart2 = Cart()
    cart2.add("MUG-01", 3)
    assert cart2.subtotal() == 3750
    assert type(cart2.subtotal()) is int


def test_format_money_converts_cents_to_dollar_string():
    assert format_money(0) == "$0.00"
    assert format_money(5) == "$0.05"
    assert format_money(1999) == "$19.99"
    assert format_money(123450) == "$1,234.50"
    assert format_money(-250) == "-$2.50"


def test_order_total_and_gateway_charge_are_integer_cents():
    # Two TEE-01 at 1999 cents each = 3998 cents subtotal
    # Shipping: 500 cents (below 5000 threshold)
    # Tax US-CA: apply_rate(3998, 0.0725) = 290 cents
    # Total: 3998 + 500 + 290 = 4788 cents
    cart = Cart()
    cart.add("TEE-01", 2)
    gateway = PaymentGateway()
    order = place_order(cart, "cus_1", "US-CA", gateway)

    assert order.total == 4788
    assert type(order.total) is int
    # The gateway must receive integer cents equal to the order total
    assert gateway.charges[0].amount_cents == 4788
    assert gateway.charges[0].amount_cents == order.total

    # Order line prices are int cents
    line = order.lines[0]
    assert line.unit_price == 1999
    assert line.line_total == 3998
    assert type(line.unit_price) is int
    assert type(line.line_total) is int
