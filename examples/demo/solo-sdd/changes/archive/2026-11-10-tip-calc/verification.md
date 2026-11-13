## Live Scenario

1. `python3 tip.py 40 15` → `tip 6.00, total 46.00`, code 0.
2. `python3 tip.py 10.10 15` → `tip 1.52, total 11.62`.
3. `python3 tip.py -5 15` → code 2, stderr names the bill, stdout empty.
4. `python3 -m unittest discover -s tests` → code 0.

## Needs

none

## Fallback

Not needed: the scenario needs nothing external.

## Result

2026-11-10: all four steps ran in the project folder. Step 1 printed `tip 6.00, total 46.00`; step 2 printed `tip 1.52, total 11.62`; step 3 exited with code 2 and `argument bill: must be a non-negative number: '-5'` on stderr; step 4 ran 4 tests, OK.

## Not Verified

nothing

## Decisions Without Owner

- A percent above 100 is allowed: a generous tip is not wrong input.
- `nan` and `inf` are refused as not a number of money.
