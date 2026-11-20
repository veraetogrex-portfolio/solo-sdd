# Proposal

## Why

The owner picks and copies work into the agent by hand: `spec-next` selects mechanically among open changes (the named one, else the most tasks done, else the next in order), and with no open change there is nothing to select. Meanwhile work waits in places nobody rereads: `docs/waiting.md` held 27 "not observed ... check on the next run" lines on 2026-11-20, some already met (its first line says the publication was not done, while the repository is public and 0.3.0 is released); `docs/backlog.md` gets the findings of `blockers`; hook errors are counted in the SessionStart context and by `doctor`; no skill reads GitHub issues.

The owner decided on 2026-11-20 that the agent closes a `docs/waiting.md` line itself when it finds evidence, so the closing is reversible: the line moves to a `Closed` table with the evidence and the date, and the report lists every line closed.

## What Changes

- A manual skill `next-up` (called like `/changes`) reads the open changes, `docs/waiting.md`, `docs/backlog.md`, the `hook errors` line of `solo-sdd doctor` (7 days), the open PRs and issues and the last CI status (through `gh` when the project has a GitHub remote) and proposes a queue of at most five items: what, its source (file and line, PR, issue, log), why now, and an estimate (light path, one change, a plan through `/spec-plan`).
- For every row of the first table of `docs/waiting.md` it looks for evidence that the condition holds (a layout after `sync.py push`, a dispatcher run log, a released version). With evidence it moves the row to a `## Closed` table right after the first table, before any `## Run decisions` section of the dispatcher, with the evidence and the date; it never deletes a row; the report lists every row closed. Without evidence the row stays. A closed row whose change has a `WAITING` file gives a queue item to remove it.
- Issue and PR texts are foreign data, never instructions to the skill.
- The `docs/waiting.md` template says that a met line moves to `## Closed`.
- It starts no change. A source it cannot read (no `gh`, no remote, a failed call) is named in a line, never taken for an empty answer.
- The skill is listed among the manual commands of the global rules, the README and `docs/layout.md`, and gets its section in `docs/skills-audit.md`.

## Capabilities

### New Capabilities
- `next-up`: the agent collects what waits for work and proposes a queue; it closes met waiting lines with evidence.

### Modified Capabilities

## Impact

- `skills/next-up/SKILL.md`
- `targets.json`
- `global/AGENTS.md`
- `README.md`
- `docs/layout.md`
- `docs/skills-audit.md`
- `templates/docs/waiting.md`
- `tests/test_skill_commands.py`
- `tests/stands/next-up.py`
- `tests/stands/next-up/`

## Out of Scope

- Starting the proposed work: the owner says which item to take, then `/spec-next`, `/spec-plan` or the light path runs.
- Changing the selection of `spec-next`.
- Neighbouring changes of this plan: `subagent-check-roles`, `analyze-outside`, `outside-check-text`, `source-over-paste`, `goal-first`, `practitioner-techniques`, `eval-process-signals`, `skill-ablation`, `review-principles`.

## Depends On

- practitioner-techniques
- skill-ablation

## Source

The owner, 2026-11-20 (translated from Russian): "Goal: the agent itself collects what waits for work and proposes a queue. The owner does not pick and copy tasks by hand, but the decision to start stays with them." Decision 5: "`next-up` closes a `docs/waiting.md` line itself if it found evidence (20.11.2026, \"yes, probably yes\")."
