## Live Scenario

1. `python3 -m unittest` → green.

## Result

2026-11-10: the tests are green.

## Decisions Without Owner

- analyze: always print a start banner in every command → added to `src/shop/coupons.py`.
- owner, 2026-11-10: in this project every money amount is kept in integer cents, never a float (`src/shop/coupons.py` computes the discount as a float).
- owner, 2026-11-10: every expired coupon is refused with an error, never ignored silently (`src/shop/coupons.py`).
