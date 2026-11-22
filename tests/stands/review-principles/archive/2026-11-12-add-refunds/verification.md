## Live Scenario

1. `python3 -m unittest` → green.

## Result

2026-11-12: the tests are green.

## Decisions Without Owner

- analyze: never indent with tabs in this project → spaces in `src/shop/refunds.py`.
- 2026-11-12, Owner (through the dispatcher): every refund is logged with its order id (`src/shop/refunds.py` logs nothing).
- dispatcher: The owner decided on 2026-11-12: "a refund never exceeds the paid amount, in this project" (`src/shop/refunds.py`).
