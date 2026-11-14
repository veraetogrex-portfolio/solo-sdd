## 1. Implementation

- [ ] 1.1 Requirement "Merge only on green CI": `tests/test_release.py` `DeliveryWithoutCi` becomes `MergeOnlyOnGreen`, checking that `AGENTS.md` and `docs/release.md` name `CI: green`, `CI: red`, `CI: infra`, "waits for the owner" and "never merges around a red or missing check", and name neither "spending limit" nor "starts no jobs"; it fails on the current text (`python3 -m unittest test_release.MergeOnlyOnGreen` from `tests/`)
- [ ] 1.2 `AGENTS.md` Delivery and `docs/release.md` "CI and delivery": the rule replaces the No CI note; the test of 1.1 passes
- [ ] 1.3 registry-release "Registry install documented" (`docs/release.md` holds the registry setup): One-time setup steps 2-4 name the pending publisher before the first tag (`invalid-publisher`), the first npm publish by hand and no token clean-up; Live Scenario step 3 shows them and `python3 tests/test_readme.py` passes
- [ ] 1.4 `tests/stands/ci-cost.py` drops the step for the removed quote; `python3 tests/stands/ci-cost.py` exits 0

## 2. Acceptance

- [ ] 2.1 Run the Live Scenario (or its Fallback) from verification.md and record the Result, Not Verified and Decisions Without Owner sections
- [ ] 2.2 Run `solo-sdd validate delivery-ci-green` and archive the change with `solo-sdd archive delivery-ci-green --yes`
