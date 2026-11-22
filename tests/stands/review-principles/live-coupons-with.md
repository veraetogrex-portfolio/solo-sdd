src/shop/coupons.py:10 — `coupon["percent"]` is never checked: a percent above 100 gives a negative total and a negative percent raises the total. It needs to be limited to 0..100 or rejected.
src/shop/coupons.py:10 — the money is worked out in float (`total * (1 - percent / 100.0)`), so totals come out with fractional cents and are never rounded. It should use `Decimal` and round to cents.
src/shop/coupons.py:8 — the comparison is `<`, so a coupon is still applied on its `expires` day. If that is intended it should be written down in the docstring. If `expires` is a `datetime` and `today` is a `date`, the comparison raises `TypeError`.
src/shop/coupons.py:5 — the diff adds no test for `apply_coupon`, so expiry, the percent bounds and rounding go unchecked.
REVIEW.md rules 1-3: no violation. There is no bare `except`, no file is opened, and both the module and `apply_coupon` have docstrings.
Important: 2
