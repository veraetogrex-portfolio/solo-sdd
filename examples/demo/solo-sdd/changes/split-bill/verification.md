## Live Scenario

1. `python3 tip.py 40 15 --people 4` → `tip 6.00, total 46.00`, then `each 11.50`, code 0.
2. `python3 tip.py 100 0 --people 3` → the second line `each 33.34`, code 0.
3. `python3 tip.py 40 15 --people 0` → code 2, stdout empty, stderr says that `--people` must be a whole number from 1.
4. `python3 tip.py 40 15` → one line `tip 6.00, total 46.00`, as before the change, code 0.
5. `python3 -m unittest discover -s tests` → code 0.

## Needs

none

## Fallback

Not needed: the scenario needs nothing external.

## Result

<!-- Filled during apply: date, what was run, what was observed. -->

## Not Verified

<!-- Filled during apply: what stayed unproven and why. Write: nothing - if all proven. -->

## Decisions Without Owner

<!-- Filled during apply: choices made without asking, and new changes created for out-of-scope work. -->
