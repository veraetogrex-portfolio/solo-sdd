src/shop/coupons.py:10 — Important: `coupon["percent"]` is never checked. A percent above 100 makes the total negative, and a negative percent raises the price.
src/shop/coupons.py:10 — Important: money is computed in binary float (`total * (1 - p / 100.0)`) with no rounding to cents, so totals come out as values like 89.99999999999999. Use Decimal and round to the currency's minor unit.
src/shop/coupons.py:1 — Important: the commit adds a new pricing function and no tests. Nothing checks the expiry boundary, the percent bounds or the rounding.
src/shop/coupons.py:8 — Minor: if `coupon["expires"]` is a datetime and `today` is a date, the comparison raises TypeError. Whether the expiry day itself counts as valid (`<` versus `<=`) is not documented.
src/shop/coupons.py:8 — Minor: a coupon without an "expires" or "percent" key raises KeyError instead of being rejected with a clear error.
Important: 3
