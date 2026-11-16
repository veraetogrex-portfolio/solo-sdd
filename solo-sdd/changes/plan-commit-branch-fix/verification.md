## Live Scenario

1. `python3 tests/test_skill_commands.py` with the step 9 text of the base commit `af6bd62` (pinned by hash, read with `git show af6bd62:skills/spec-plan/SKILL.md`) → the new row fails: step 9 names no `plan/` branch; on the change branch → passes.
2. A temporary git repository with a bare remote, `solo-sdd init`, `AGENTS.md` with `## Delivery` and `- Mode: pr`, `main` checked out and pushed; `claude -p --model haiku` runs `/spec-plan` with the input "add a CSV export" and the instruction to stop before `ship` → `git rev-parse main` is unchanged, `git log -1 --format=%s plan/<id>` prints `change: <id>`, and the report has the line `Plan: commit <hash> on plan/<id>`.
3. The same repository with `- Mode: local` → the plan commit is the last commit of `main`.

## Needs

- Steps 2-3: two paid Claude Code runs on the cheapest model (haiku), about USD 0.10 in all; the owner's approval.

## Fallback

- Steps 2-3 without approval: the agent follows the edited step 9 by hand in the same temporary repository, without a model call, and records the refs `main` and `plan/<id>` before and after; the model run goes into `Not Verified` and `docs/waiting.md`.

## Result

<!-- Filled during apply: date, what was run, what was observed. -->

## Not Verified

<!-- Filled during apply: what stayed unproven and why. Write: nothing - if all proven. -->

## Decisions Without Owner

- plan: the branch is `plan/<first id>` → the earlier plan PRs of this repository used `plan/<name>`, and `change/<id>` is taken by the change's own worktree of `sdd-worktree.py`.
- plan: delivery of the branch stays in `ship` → `ship` already holds the PR tool, the CI wait and the merge rules; step 9 only names the branch and hands it over.
