Result: tip.py rounds money correctly under its stated rule. The tip is bill × percent / 100, rounded half-up to cents, and the total is bill plus that rounded tip. `python3 tip.py 10.10 15` prints `tip 1.52, total 11.62` (exact 1.515 rounds up). The 4 existing tests pass. Nothing was changed.

Practitioner checks:
- Exact decimal arithmetic, not float — https://docs.python.org/3/library/decimal.html
- Explicit rounding mode, half-up vs half-even — https://docs.python.org/3/library/decimal.html#rounding-modes
- Money in currency minor units (2 places for USD, EUR, RUB) — ISO 4217

Practitioner checks run: exact decimal vs float: float gives 1.51 for 10.10 at 15%, the code gives 1.52 (Decimal is correct); rounding modes: half-even would give 0.02 for 0.25 at 10%, the code gives 0.03; boundary cases: 0.05 at 10% → tip 0.01, 0.15 → 0.02, 0.25 → 0.03, 99.99 at 33.3% → tip 33.30, total 133.29, all correct under half-up.
Practitioner checks not run: ISO 4217 minor units — the code accepts bills with more than 2 decimals (`1.005 0` gives total 1.01); this is an input-validation gap, not a tip-rounding error, and it was left as is because the request is analysis only.

Findings:
- The half-up choice is explicit in tip.py and asserted in tests/test_tip.py, so it is a deliberate rule, not an accident. Half-even would change exact-half cases such as 0.25 at 10%.
- Not confirmed: solo-sdd/specs/ is empty in this copy, so there is no written spec for rounding. "Right" is judged from the code, the tests and the project intent in solo-sdd/project.md ("reads the right tip and total").
- Skipped: restricting bills to cents. Add it when bills come from a real till, if sub-cent input should be refused.

Not run: `solo-sdd validate --all` (this was an analysis, so no change check was run). No lesson written; no AGENTS.md change.

Files: /tmp/practitioner-techniques.0ayg2et2/demo/tip.py, /tmp/practitioner-techniques.0ayg2et2/demo/tests/test_tip.py, /tmp/practitioner-techniques.0ayg2et2/demo/AGENTS.md.
