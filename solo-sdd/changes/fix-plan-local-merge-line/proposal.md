# Proposal

## Why

Reproduction (found in the settings-* run, 2026-11-17; read in code on 2026-11-18):
1. A project with `delivery.mode: local` and `delivery.merge: rebase` runs `sdd-dispatch-plan.py <MAIN>`.
2. Expected: the third line names the method `land-local` uses, `delivery.local-merge`. The Local merge method requirement says `delivery.merge` describes only pull requests.
3. Got: `delivery: local (file), merge: rebase (file)`. The dispatcher reads `rebase` as the merge method, while `land-local` merges with `--no-ff` by the default `delivery.local-merge: merge`.

Cause: `global/sdd_dispatch_plan.py:827` always prints `deliver["delivery.merge"]`, whatever the mode. The plan's settings registry copy holds `delivery.local-merge` (`global/sdd_dispatch_plan.py:63`), but `render` never uses it. `skills/spec-dispatch/preparation.md` describes the same line with the PR method only.

## What Changes

- In `local` mode the third plan line is `delivery: local (<source>), local merge: <delivery.local-merge> (<source>)`.
- The `pr` line is unchanged.
- `skills/spec-dispatch/preparation.md` and the script's docstring name both forms.

## Capabilities

### New Capabilities

### Modified Capabilities
- `settings`: MODIFIED requirement Local merge method (new scenarios The plan line in local mode, The plan line in pr mode).

## Impact

- `global/sdd_dispatch_plan.py`
- `tests/test_sdd_dispatch_plan.py`
- `skills/spec-dispatch/preparation.md`
- `tests/stands/plan-local-merge-line.py`

## Out of Scope

- How `land-local` merges: it already reads `delivery.local-merge` itself.
- Neighbouring changes of this plan: `test-runner-deps-check`, `dispatched-status-self-check`, `fix-settings-entry-scroll`, `fix-worktree-ignored-overwrite`, `fix-ci-wait-unread-checks`, `fix-stop-gate-worktree-config`, `fix-setup-links-exclude`.

## Depends On

none

## Source

"Да, заведи change" (the owner, 2026-11-18, on the follow-up list after the settings-* run, item: `sdd_dispatch_plan.py` still prints `merge: <delivery.merge>` in local mode)
