# Proposal

## Why

`spec-analyze` runs in the session that wrote or is about to implement the change: `spec-plan` step 7a has the planner check its own artifacts and mark them "Ready for implementation", `spec-next` step 4a has the executor check the change it codes right after. `spec-analyze` itself has no subagent step ("Ask no questions. Fix CRITICAL and HIGH yourself"). A session judges its own work poorly, and one pass in one context finds what that context already expects.

The owner decided on 2026-11-20 to run the check outside the author: attackers on a cheap model, each on its own pass group, and a judge on the main model that keeps or drops their findings before the author edits the artifacts; three attackers by default.

## What Changes

- `spec-analyze` gets an outside run: the author launches `Analyze: <id>` in a clean subagent with the artifact paths, the main specs of the affected capabilities and the project rules, and no planner reasoning, reports or chat history.
- With `process.analyze-attackers` N > 0 (default 3) the author launches N `Attack: <id> <passes>` subagents instead, each on its own pass group (coverage, frame and checkability 1, 2, 3, 3a; consumer and trust boundary 4, 4a; ambiguities, wording and compatibility 5, 6, 7, 7a, 7b), each tasked to prove the change is not ready; then one `Judge: <id>` subagent gets all findings and the artifacts and marks every finding `keep` with a level or `drop` with a reason, merging duplicates. N = 0 runs the single `Analyze:`.
- Attackers run on `agents.attack-model`, the analyzer and the judge on the main model (or `agents.review-model`). Inside these subagents, on a direct `/spec-analyze` call and in an agent without a subagent tool the passes run in place.
- The author fixes every kept CRITICAL and HIGH in the artifacts; a kept finding it does not fix gets a line in `Decisions Without Owner`. The repeat of passes 1, 2, 7 and 7a after the edits runs in one `Analyze:` subagent. The report line becomes `Analyze: <n> findings, kept <k>, dropped <d>; CRITICAL <c> · HIGH <h>, fixed <f>`.
- The subagent limits of `spec-next` (step 5, the dispatched mode), `ALGORITHM.md` and section 10 of the global rules name the three tags.
- `spec-plan` step 7a and `spec-next` step 4a run `spec-analyze` this way; the procedure lives in `spec-analyze`, so `spec-plan` stays within the skill size budget.
- A new setting `process.analyze-attackers` (integer, at least 0, default 3); an agent changes it only on the owner's words in the chat, like `process.analyze`.
- A stand with a change that holds four planted holes compares the run in the same session, one `Analyze:`, and three `Attack:` with a `Judge:`.

## Capabilities

### New Capabilities
- `analyze-outside`: spec-analyze runs outside the author, with attackers and a judge.

### Modified Capabilities
- `settings`: ADDED requirement Analyze attackers setting; MODIFIED requirement Process cadence settings.
- `spec-next`: MODIFIED requirement Lead writes code.
- `spec-next-dispatched`: MODIFIED requirement Orchestrator writes code.

## Impact

- `skills/spec-analyze/SKILL.md`
- `skills/spec-plan/SKILL.md`
- `skills/spec-next/SKILL.md`
- `ALGORITHM.md`
- `global/AGENTS.md`
- `targets.json`
- `tests/affected.json`
- `solo_sdd/settings.py`
- `global/work_hooks.py`
- `global/sdd_dispatch_plan.py`
- `global/sdd_pr.py`
- `global/sdd_worktree.py`
- `docs/settings.md`
- `tests/test_settings.py`
- `tests/test_skill_commands.py`
- `tests/stands/analyze-outside.py`
- `tests/stands/analyze-outside/`

## Out of Scope

- The hook roles `Analyze:`, `Attack:`, `Judge:` and their models: `subagent-check-roles`.
- Attackers on the code review of `spec-next` step 7a: a separate change once this stand shows a gain on specs.
- Counting the `Analyze:` line in `sdd-eval.py metrics`: `eval-process-signals`.
- Neighbouring changes of this plan: `subagent-check-roles`, `outside-check-text`, `source-over-paste`, `goal-first`, `practitioner-techniques`, `eval-process-signals`, `skill-ablation`, `work-pull`, `review-principles`.

## Depends On

- subagent-check-roles
- lesson-merge-by-cause

## Source

The owner, 2026-11-20 (translated from Russian): "Goal: the spec before code is checked by a session other than the one that wrote it; the findings go through the judge's filter before the artifacts are edited." Decisions 3 and 4: "Attackers (`Attack:`) run on a cheap model; the judge and acceptance stay on the main one (20.11.2026)." "3 attackers by default: `process.analyze-attackers` = `3` (20.11.2026)."
