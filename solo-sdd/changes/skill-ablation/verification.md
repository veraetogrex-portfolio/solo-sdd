## Live Scenario

1. `python3 tests/test_skill_commands.py` → the audit table test passes: every skill of `targets.json` has a section in `docs/skills-audit.md`, every step its row with one of the three marks, every `hook: yes` row in `Gates a hook could hold`.
2. `python3 tests/stands/skill-ablation.py debug-profile --budget 6` → the probe passes (`claude -p` runs logged in from the runner's isolated folder, and in the cut variants the session cannot load the full skill); 6 task calls on the subscription (2 tasks by 3 variants); a table of 6 rows with the outcome, the path and the tokens; exit 0. The table goes into `docs/skills-audit.md` with the date and the main model.
3. `python3 tests/stands/skill-ablation.py evidence-research --budget 6` → the same for `evidence-research`.
4. `python3 tests/stands/skill-ablation.py evidence-research --budget 4` → 4 rows and `budget reached: 2 of 6 calls not made`, exit 3.

## Needs

- The owner's budget for one runner run (tasks and calls on the subscription); this plan assumes 6 task calls per skill, 12 in all, plus one probe per variant, no paid API calls; a terminal logged in to Claude.

## Fallback

Without the budget or a logged-in `claude -p`: steps 2-4 run with a fake `claude` first on `PATH` (a script that writes a canned answer, the loaded skill list and usage per variant), which proves the variants, the method step stripping, the leak probe, the checks, the table and the budget stop; `Not Verified` names the real runs, and `docs/waiting.md` gets a line for them.

## Result

<!-- Filled during apply: date, what was run, what was observed. -->

## Not Verified

<!-- Filled during apply: what stayed unproven and why. Write: nothing - if all proven. -->

## Decisions Without Owner

<!-- Filled during apply: choices made without asking, and new changes created for out-of-scope work. -->

- analyze: order → after `eval-process-signals`: the audit table test reads every skill step, so it lands after the plan's skill edits; `tests/test_skill_commands.py` and `tests/affected.json` are shared with them.
- analyze: the owner did not name the budget of a runner run → 6 task calls per skill, 12 in all, plus one probe per variant, on the subscription; `Needs` names it, and the real run waits for the owner's word.
