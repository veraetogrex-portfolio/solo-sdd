## Live Scenario

The lead session runs every prepared prompt as an `Agent` subagent without `model` (the main model, the one measured), described `Ablation: <skill> <variant> <task>`, and saves its answer and transcript path into the run folder.

1. `python3 tests/test_skill_commands.py` → the audit table test passes: every skill of `targets.json` has a section in `docs/skills-audit.md`, every step its row with one of the three marks, every `hook: yes` row in `Gates a hook could hold`.
2. `python3 tests/stands/skill-ablation.py prepare debug-profile --budget 6` → 6 prompts (2 tasks by 3 variants), exit 0; the lead runs them as 6 subagents; `python3 tests/stands/skill-ablation.py grade <run>` → a table of 6 rows with the outcome, the path and the tokens, no `not run` row. The table goes into `docs/skills-audit.md` with the date and the main model.
3. The same for `evidence-research`.
4. `python3 tests/stands/skill-ablation.py prepare evidence-research --budget 4` → 4 prompts and `budget reached: 2 of 6 calls not made`, exit 3.

## Needs

- 12 subagent runs in the Claude Code session on the subscription (6 per skill), allowed by the owner on 2026-11-20 only as Claude Code subagents; no `claude -p`, no paid API calls.

## Fallback

Not needed: the subagents run in the lead session. A subagent that fails or is stopped leaves a `not run` row, named in `Not Verified`.

## Result

<!-- Filled during apply: date, what was run, what was observed. -->

## Not Verified

<!-- Filled during apply: what stayed unproven and why. Write: nothing - if all proven. -->

## Decisions Without Owner

<!-- Filled during apply: choices made without asking, and new changes created for out-of-scope work. -->

- analyze: order → after `eval-process-signals`: the audit table test reads every skill step, so it lands after the plan's skill edits; `tests/test_skill_commands.py` and `tests/affected.json` are shared with them.
- analyze: the runner's budget → 12 subagent runs (6 per skill); the owner allowed runs only as Claude Code subagents (2026-11-20), so the runner prepares prompts and grades answers, and `claude -p` is not used.
