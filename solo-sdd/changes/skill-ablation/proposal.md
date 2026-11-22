# Proposal

## Why

A skill written for one model can stop helping the next one, and sometimes the model does better without it. solo-sdd ships 20 skills (145,850 bytes on 2026-11-20; the largest `spec-plan` 15,943, `spec-dispatch` 15,798, `project-init` 14,944, `spec-next` 14,784), and nothing measures what each gives the current main model. The eval set cannot answer it: its configurations set only Working copy lines and cannot switch a skill off, and a full replay costs 4-7 h and about $80-200 per run with no baseline yet. Skills hold two kinds of steps: gates (a condition without which a step is not closed, some already enforced by code) and methods (how to think and in what order); methods age first.

## What Changes

- `docs/skills-audit.md`: every skill and each of its steps marked `gate (code)`, `gate (text)` or `method`; a `gate (text)` step also says whether a hook or the CLI could enforce it, and those are listed at the end for the owner to plan as changes.
- `tests/stands/skill-ablation.py`: for one skill and a task set with checkable outcomes, prepares prompts for three variants, each run by a Claude Code subagent of the lead session (never `claude -p`, by the owner's decision of 2026-11-20): the full skill; the skill without its `method` steps (by the table); no skill. All three share the lead session's context (the laid-out global rules, the project rules, the skill listing) and carry their text inline. `grade` checks each saved answer by the task's script and the path (whether the required commands ran, from the subagent's transcript) and prints a table variant by task with tokens. A row whose subagent loaded the skill or read the task sets anyway is marked `leaked` and left out. `prepare` writes no prompt beyond `--budget`.
- Task sets for `debug-profile` and `evidence-research` (methods whose outcomes a script can check).
- The runner refuses a skill outside `targets.json` and a manifest it did not write, and grades a broken transcript as `unreadable`; `tests/stands/skill-ablation/stand.py` runs prepare and grade end to end on transcripts made from the reference answers.
- `docs/release.md`: when the `main` list of `model-policy.json` changes, the runner runs on every skill with a task set and the result goes into `docs/skills-audit.md`; a skill that did not beat the no-skill variant on two runs in a row is listed as a candidate to cut, and only the owner removes the line or the skill.

## Capabilities

### New Capabilities
- `skill-ablation`: what each skill gives the current main model, measured by switching it off.

### Modified Capabilities

## Impact

- `docs/skills-audit.md`
- `docs/release.md`
- `tests/stands/skill-ablation.py`
- `tests/stands/skill-ablation/`
- `tests/test_skill_ablation.py`
- `tests/test_skill_commands.py`
- `tests/affected.json`

## Out of Scope

- A `spec-analyze` task set on the fixture of `analyze-outside`: a follow-up once both are archived.
- Deleting or cutting any skill: only the owner decides, on the runner's table.
- Replays of the eval set (`sdd-eval.py`): they wait for the baseline in `docs/waiting.md`.
- Neighbouring changes of this plan: `subagent-check-roles`, `analyze-outside`, `outside-check-text`, `source-over-paste`, `goal-first`, `practitioner-techniques`, `eval-process-signals`, `work-pull`, `review-principles`.

## Depends On

- eval-process-signals

## Source

The owner, 2026-11-20 (translated from Russian), on the runner's budget: "Only if these are subagents in Claude Code." Earlier: "Turn into changes four techniques from the interview: attacking reviewers with a judge, a check of whether skills get in the way, a set of the owner's review rules, the agent choosing tasks." Unit B: "Goal: for every skill it is known what it gives the current main model. The measurement is repeated when the main model changes."
