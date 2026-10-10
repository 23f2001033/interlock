"""Test that change X's intent holds: currency recording and Maharashtra support."""

import pytest

from shop.cart import Cart
from shop.payments import PaymentGateway
from shop.pricing import quote, tax_for
from shop.orders import place_order


def test_charge_records_currency_with_default_usd():
    """Charges default to USD currency."""
    gateway = PaymentGateway()
    charge_id = gateway.charge("cus_1", 5000)
    assert gateway.charges[0].currency == "USD"


def test_charge_records_explicit_currency():
    """Callers can pass explicit currency to charge()."""
    gateway = PaymentGateway()
    gateway.charge("cus_1", 5000, currency="EUR")
    gateway.charge("cus_1", 7000, "GBP")
    assert [c.currency for c in gateway.charges] == ["EUR", "GBP"]


@pytest.mark.parametrize("currency", ["usd", "US", "USDX", "", "U$D", None])
def test_charge_rejects_invalid_currency(currency):
    """Invalid currency codes are rejected."""
    gateway = PaymentGateway()
    with pytest.raises(ValueError):
        gateway.charge("cus_1", 5000, currency)


def test_maharashtra_tax_rate():
    """IN-MH region has 18% tax rate."""
    assert tax_for(10000, "IN-MH") == 1800


def test_quote_in_maharashtra():
    """Carts can be quoted in Maharashtra region."""
    cart = Cart()
    cart.add("TEE-01", 2)
    q = quote(cart, "IN-MH")
    assert q["tax"] == 7.2
    assert q["total"] == 52.18


def test_order_in_maharashtra():
    """Orders can be placed in Maharashtra region."""
    cart = Cart()
    cart.add("TEE-01", 2)
    gateway = PaymentGateway()
    order = place_order(cart, "cus_1", "IN-MH", gateway)
    assert order.region == "IN-MH"
    assert order.tax == 7.2
    assert order.total == 52.18
    assert gateway.charges[0].amount_cents == 5218
