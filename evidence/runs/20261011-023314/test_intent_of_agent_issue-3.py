"""Tests for the SAVE10 discount code feature (Change X)."""

import pytest

from shop.cart import Cart
from shop.payments import PaymentGateway
from shop.orders import place_order
from shop.receipts import render_receipt


def test_save10_discount_applied_to_qualifying_order():
    """SAVE10 gives 10% off a subtotal >= $40, tax is on the discounted subtotal,
    and the gateway is charged the discounted total."""
    cart = Cart()
    cart.add("MUG-01", 2)   # 2 x $12.50 = $25.00
    cart.add("CAP-01")      # 1 x $15.00 = $15.00  => subtotal $40.00
    gateway = PaymentGateway()
    order = place_order(cart, "cus_1", "US-CA", gateway, code="SAVE10")

    # Discount must be 10% of $40.00 = $4.00
    # Tax is 7.25% of ($40.00 - $4.00) = 7.25% of $36.00 = $2.61
    # Total = $40.00 - $4.00 + $5.00 shipping + $2.61 tax = $43.61
    # We compare in whatever unit the implementation uses; we check the receipt
    # for human-readable correctness and the gateway charge for the right amount.
    receipt = render_receipt(order)
    assert "Subtotal: $40.00" in receipt
    assert "Discount: -$4.00" in receipt
    assert "Tax (US-CA): $2.61" in receipt
    assert "Total: $43.61" in receipt

    # Gateway must be charged exactly the discounted total (4361 cents)
    assert len(gateway.charges) == 1
    assert gateway.charges[0].amount_cents == 4361


def test_save10_not_applied_below_minimum():
    """SAVE10 gives no discount when the subtotal is below $40.00."""
    cart = Cart()
    cart.add("TEE-01", 2)   # 2 x $19.99 = $39.98 — just below the $40 minimum
    gateway = PaymentGateway()
    order = place_order(cart, "cus_2", "US-CA", gateway, code="SAVE10")

    receipt = render_receipt(order)
    # No discount line should appear
    assert "Discount" not in receipt
    # Total should be the same as without any code
    assert "Total: $47.88" in receipt


def test_unknown_discount_code_raises_and_does_not_charge():
    """An unknown discount code raises ValueError before any charge is made."""
    cart = Cart()
    cart.add("MUG-01", 4)
    gateway = PaymentGateway()
    with pytest.raises(ValueError):
        place_order(cart, "cus_3", "US-NY", gateway, code="BOGUS")
    assert gateway.charges == []
