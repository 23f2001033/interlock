# Represent money as integer cents end-to-end (#1)

We keep seeing 1-cent mismatches between quoted totals and what the gateway charges, because amounts are floats in dollars.

Switch the shop to integer cents everywhere: catalog prices, cart subtotal, shipping, tax, quote totals and order amounts should all be `int` cents. Convert to a dollar string only when displaying (receipts). Keep behavior the same for customers (same prices, same rounding of tax to the nearest cent). Update the tests.
