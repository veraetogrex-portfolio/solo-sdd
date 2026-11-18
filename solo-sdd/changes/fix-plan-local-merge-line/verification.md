## Live Scenario

1. `python3 tests/stands/plan-local-merge-line.py` → the stand builds a temporary project with `solo-sdd/config` holding `delivery.mode: local` and `delivery.merge: rebase`, and one open change. It runs the repository's `global/sdd_dispatch_plan.py` on it, and the third line is `delivery: local (file), local merge: merge (default)`. On the previous code it is `delivery: local (file), merge: rebase (file)`.
2. It adds `delivery.local-merge: squash`, and the line becomes `delivery: local (file), local merge: squash (file)`.
3. It sets `delivery.mode: pr`, and the line is `delivery: pr (file), merge: rebase (file)`. The stand prints `plan-local-merge-line: 3 of 3 checks passed`.

## Needs

none

## Fallback

Not needed: the stand runs locally without access or paid calls.

## Result

<!-- Filled during apply: date, what was run, what was observed. -->

## Not Verified

<!-- Filled during apply: what stayed unproven and why. Write: nothing - if all proven. -->

## Decisions Without Owner

<!-- Filled during apply: choices made without asking, and new changes created for out-of-scope work. -->
