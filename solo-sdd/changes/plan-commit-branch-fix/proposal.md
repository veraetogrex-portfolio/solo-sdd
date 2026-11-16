# Proposal

## Why

Reproduction, 16.11.2026, in this repository (`delivery.mode` `pr`, source `AGENTS.md`): `/spec-plan` created `skill-compaction-budget` and, by step 9, committed it on the checked-out `main` (`1069a31`) → expected the plan to reach `origin/main` through a PR, the only delivery `pr` allows → got a local `main` one commit ahead of `origin/main`, not pushed, while another session's dispatcher was running worktrees and merges against the same `main`.

Cause: `skills/spec-plan/SKILL.md:75`, step 9 "Plan commit" runs `git commit` in the working folder on whatever branch is checked out and stops there; it never reads `delivery.mode` and never hands the commit to `ship`. Main spec `spec-plan`, requirement Plan committed, describes the commit but not the branch it lands on. The repair in the same session then opened the PR with `gh pr create` on a branch named `change/<id>`, the name `sdd-worktree.py` gives to the change's own worktree, because the step names neither the branch nor the PR tool.

## What Changes

- Step 9 of `skills/spec-plan/SKILL.md`: under `delivery.mode` `pr` the plan commit is made in a temporary worktree on a new branch `plan/<first id>` from the main branch, the checked-out branch of the working folder does not move, and `ship` delivers the branch through `sdd-pr.py` (open, wait, merge by `delivery.merge-by`); after the merge the temporary worktree is removed and the local main branch is pulled; under `local` the commit stays on the main branch as now and `ship` pushes it.
- The report line `Plan:` names the branch and the PR (`commit <hash> on plan/<id>, PR <url>`), and `waits for human merge` when a person merges.

## Capabilities

### New Capabilities

### Modified Capabilities
- `spec-plan`: requirement Plan committed names the branch under `delivery.mode` `pr`.

## Impact

`skills/spec-plan/SKILL.md`, `tests/test_skill_commands.py`.

## Out of Scope

- `skill-compaction-budget`: it moves the long steps of `spec-plan` into step files and depends on this change.
- The light path of the global rules: it already says the PR title starts with `light:` under `delivery.mode: pr`.
- A guard hook that refuses `gh pr create` in a project with `solo-sdd/`: `ship` already forbids it in words; a hook is a separate decision.

## Depends On

none

## Source

The owner, 16.11.2026: "you left a mess and did not clean up after yourself" (translated from Russian), then "Yes, make it" to the question whether to make a bug fix change for spec-plan step 9 committing the plan to main in PR mode.
