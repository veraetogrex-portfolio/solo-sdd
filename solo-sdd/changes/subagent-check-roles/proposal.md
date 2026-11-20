# Proposal

## Why

Two planned outside checks need a subagent that is neither a reviewer nor a search: `spec-analyze` in a clean context with attackers and a judge (`analyze-outside`), and a fact check of analyses and texts (`outside-check-text`). Under the dispatcher an orchestrator subagent may launch only `Review:` and `Lookup:` agents (`global/work_hooks.py:1761-1763`), and the `Review:` tag cannot be reused: the archive gate counts any agent of the review role after the first code edit as the code review (`global/work_hooks.py:1289`), so a spec analysis or a fact check under that tag would open the archive without a review of the code.

The owner decided on 2026-11-20: attackers run on a cheap model, the judge and acceptance stay on the main model.

## What Changes

- `global/model-policy.json` gets four role tags: `Analyze:` (analyze), `Attack:` (attack), `Judge:` (judge), `Check:` (check).
- The guard hook allows the four roles from a subagent as well as from the main session. `Analyze:`, `Judge:` and `Check:` run without `model` or on a model of the `main` list, like `Review:`; `Attack:` runs on a model set explicitly and outside the `expensive` list, of any `subagent_type`.
- A new setting `agents.attack-model` (default `haiku`) names the attackers' model; the guard refuses a project value outside the `cheap` list, as for `agents.lookup-model`. `Analyze:`, `Judge:` and `Check:` are bounded by `agents.review-model` and the `main` list.
- None of the four roles counts as the code review of the archive gate: only a `Review:` agent after the first code edit opens the archive.
- `docs/hooks.md` names the four tags and their model rules.

## Capabilities

### New Capabilities

### Modified Capabilities
- `model-guard`: MODIFIED requirements Subagent role by description prefix, Models allowed per role and caller.
- `settings`: ADDED requirement Attack model setting; MODIFIED requirement Project models within the machine policy.
- `work-hooks-subagents`: MODIFIED requirement Review before archive.

## Impact

- `global/model-policy.json`
- `global/work_hooks.py`
- `global/sdd_dispatch_plan.py`
- `global/sdd_pr.py`
- `global/sdd_worktree.py`
- `solo_sdd/settings.py`
- `docs/hooks.md`
- `docs/settings.md`
- `tests/test_work_hooks.py`
- `tests/test_settings.py`
- `tests/stands/subagent-check-roles.py`

## Out of Scope

- The skill texts that launch the new roles: `analyze-outside` (`spec-analyze`, `spec-plan`, `spec-next`) and `outside-check-text` (global rules, `evidence-research`).
- Counting the new roles in `sdd-eval.py metrics`: `eval-process-signals`.
- Attackers on the code review of `spec-next` step 7a: a separate change after the measurement on specs.
- Neighbouring changes of this plan: `analyze-outside`, `outside-check-text`, `source-over-paste`, `goal-first`, `practitioner-techniques`, `eval-process-signals`, `skill-ablation`, `work-pull`, `review-principles`.

## Depends On

none

## Source

The owner, 2026-11-20 (translated from Russian): "New roles in `model-policy.json` and `ROLE_KEYS`: `Analyze:` (clean context, main model), `Attack:` (model from `agents.attack-model`, cheap by default), `Judge:` (main model). Allow them from the orchestrator subagent." and "New role `Check:` (main model; allowed from the orchestrator subagent) in `model-policy.json`, `ROLE_KEYS`, `docs/hooks.md`." Decision 3: "Attackers (`Attack:`) run on a cheap model; the judge and acceptance stay on the main one (20.11.2026)."
