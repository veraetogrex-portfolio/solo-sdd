## Live Scenario

1. `grep -n -e "spending limit" -e "No CI" -e "PR #79" AGENTS.md docs/release.md` → no line.
2. `grep -n "CI: green" AGENTS.md docs/release.md` → a line in each file, with "waits for the owner" and "never merges around a red or missing check" in the same paragraph.
3. `sed -n '/## One-time setup/,/## Publication/p' docs/release.md` → step 2 names `invalid-publisher` and "before the first tag"; step 3 names `npm login` and `npm publish ./dist/solo-sdd-<v>.tgz --registry https://registry.npmjs.org`.
4. `python3 tests/stands/ci-cost.py` → every line `ok`, exit 0.
5. This change's PR: `sdd-pr.py wait <url>` prints `CI: green`, then `sdd-pr.py merge` merges it, as the new text says.

## Needs

none

## Fallback

none needed

## Result

<!-- Filled during apply: date, what was run, what was observed. -->

## Not Verified

<!-- Filled during apply: what stayed unproven and why. Write: nothing - if all proven. -->

## Decisions Without Owner

- plan: REMOVED "Delivery without CI" and ADDED "Merge only on green CI" instead of turning it into an `infra` fallback with the probed output: CI runs since 2026-11-13, and the rule that matters (no merge around a red or missing check) holds for every non-green result, not only `infra`.
- analyze: task 1.3 had no requirement → tied to registry-release ("`docs/release.md` SHALL hold the registry setup"), checked by Live Scenario step 3 — a docs fix that changes no requirement.
- analyze: the green scenario met `delivery.merge-by: human` → the scenario says "where `delivery.merge-by` lets an agent merge" — green is necessary, not sufficient.
