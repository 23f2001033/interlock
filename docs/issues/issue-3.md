# Support the SAVE10 discount code (#3)

Customers can enter the code `SAVE10` at checkout to get 10% off the subtotal, for subtotals of at least $40.00.

`place_order` should accept an optional `code` argument. The quote should show the discount as `discount` and the total should reflect it; tax is computed on the discounted subtotal. Unknown codes raise `ValueError`. Add tests.
