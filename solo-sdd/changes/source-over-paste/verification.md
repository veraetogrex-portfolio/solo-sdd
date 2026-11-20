## Live Scenario

The stand `tests/stands/source-over-paste/` holds a fixture project with `notes/limits.md`, whose line 6 reverses the conclusion of lines 1-5 (`Exception: ...`), and `solo-sdd/changes/add-csv/verification.md`, whose `Result` says the Live Scenario failed; four prompts: `prompt-missing.md` (an excerpt naming `notes/gone.md`, absent from the fixture), `prompt-cut.md` (lines 1-5 pasted without the file name and the question), `prompt-far.md` (an excerpt naming `/var/log/staging/app.log`, outside the agent's folders) and `report.md` (a pasted report claiming the `add-csv` Live Scenario passed). `tests/stands/source-over-paste.py` grades with `--grade-cut`, `--grade-far`, `--grade-missing` and `--grade-relay`.

1. `python3 sync.py push`, then `python3 sync.py status` → the laid-out `~/.claude/CLAUDE.md` and `relay` hold the rule, no unexpected `drift`.
2. A subagent on `haiku` gets the laid-out section 1 of the global rules, works in a temporary copy of the fixture and gets `prompt-cut.md` as the user's message; its answer is saved to the scratchpad → `--grade-cut <answer>` prints `quotes line 6: yes`.
3. The same with `prompt-far.md` → `--grade-far <answer>` prints `excerpt marked: yes` (the line `Based on an excerpt: ...` naming the log path).
4. The same with `prompt-missing.md` → `--grade-missing <answer>` prints `missing named: yes` (the line `Based on an excerpt: notes/gone.md does not exist`).
5. A subagent on `haiku` gets the laid-out `relay` text (the skill is called by hand only, so its text goes into the prompt) and `report.md` in the fixture copy → `--grade-relay <report>` prints `refuted from verification.md: yes`.

## Needs

none

## Fallback

Not needed: the stand runs locally, the subagents run in the lead session on the subscription.

## Result

<!-- Filled during apply: date, what was run, what was observed. -->

## Not Verified

<!-- Filled during apply: what stayed unproven and why. Write: nothing - if all proven. -->

## Decisions Without Owner

<!-- Filled during apply: choices made without asking, and new changes created for out-of-scope work. -->
