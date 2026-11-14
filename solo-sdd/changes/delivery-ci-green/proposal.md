# Proposal

## Why

`AGENTS.md` (Delivery) and `docs/release.md` ("CI and delivery without CI") still say that GitHub Actions starts no jobs because of the spending limit of the private repository (since 2026-11-08, probed on PR #79 on 2026-11-12), and the main requirement "Delivery without CI" with `tests/test_release.py` `DeliveryWithoutCi` requires that text. Since 2026-11-13 the repository is public and Actions runs: PRs #1-#4 passed `sdd-pr.py wait` with `CI: green`, and the agent merged #1-#3 through `sdd-pr.py merge` (checked with `gh run list` on 2026-11-14). The note now tells an agent to expect no CI and leave every PR to the owner.

The one-time setup of `docs/release.md` is stale too: step 3 stores an npm token that bypasses two-factor authentication, which npm refuses for a direct publish, so the first npm publish of v0.2.0 was done once by hand from the owner's terminal; and the `release` run 43575796294 of v0.2.0 failed at the PyPI upload with `invalid-publisher` (no pending publisher yet), which step 2 does not warn about.

## What Changes

- The requirement "Delivery without CI" is removed with its test; a new requirement "Merge only on green CI" keeps its rule for every result: an agent merges a PR only when `sdd-pr.py wait` gives `CI: green`; on `CI: red` or `CI: infra` the PR waits for the owner, and an agent never merges around a red or missing check.
- `AGENTS.md` Delivery: the "No CI" bullet becomes that rule.
- `docs/release.md`: the section "CI and delivery without CI" becomes "CI and delivery" with the same rule and no claim that Actions starts no jobs.
- `docs/release.md` One-time setup: step 2 says the PyPI pending publisher must exist before the first tag, or the PyPI job fails with `invalid-publisher`; step 3 says the first npm publish is done once by hand from the owner's terminal (`npm login`, then `npm publish ./dist/solo-sdd-<v>.tgz --registry https://registry.npmjs.org`) and later versions use the trusted publisher; step 4 drops the token clean-up.
- The stand `tests/stands/ci-cost.py` drops its step that checked the removed quote.

## Capabilities

### New Capabilities

### Modified Capabilities
- `publication`: "Delivery without CI" is removed, "Merge only on green CI" is added.

## Impact

`AGENTS.md`, `docs/release.md`, `solo-sdd/specs/publication/spec.md`, `tests/test_release.py`, `tests/stands/ci-cost.py`

## Out of Scope

- `.github/workflows/release.yml` and its `NPM_TOKEN` branch: workflow files are merged by the owner only; the branch stays unused while the secret is unset.
- The `release` tier failures of `tests/test_cli.py` on macOS (`Library/Caches/com.apple.python` in the home) seen on the v0.2.0 tag: a separate change.
- `sdd-pr.py` behaviour: `merge` already refuses a PR whose checks are not green (pr-tool).

## Depends On

none

## Source

"Task: In the solo-sdd repository, plan and carry out one change through `/spec-plan` and then `/spec-next`. The change removes the \"No CI\" delivery note, which is no longer true." (the session that started this one, 2026-11-14)
