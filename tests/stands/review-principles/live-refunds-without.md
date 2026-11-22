src/shop/refunds.py:21 — Important: nothing checks the refund against the order total, so repeated or large calls push `order["refunded"]` past what was paid (over-refund).
src/shop/refunds.py:21 — Important: `amount` is not checked; a negative amount lowers `refunded` (it works as a hidden charge), and zero or non-numeric values are accepted without error.
src/shop/refunds.py:19 — Important: the commit adds a money path with no test; there is no `tests/` file for refund in the diff, so neither of the two cases above is covered.
src/shop/refunds.py:21-22 — Minor: the function changes the caller's `order` dict in place and also returns it. Pick one, or document that it mutates.
Important: 3
