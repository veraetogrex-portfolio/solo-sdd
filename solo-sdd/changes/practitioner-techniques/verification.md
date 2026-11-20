## Live Scenario

`tests/stands/practitioner-techniques.py --grade <answer>` checks that an answer starts with a list of at least three practitioner checks, each with a source (a link or a named standard), and that its report names which of them ran; `--grade-plan <change>` checks a planned change's proposal for the list and a task or Live Scenario step per used item. Money rounding is the field: no spec, lesson or deployed skill covers it (checked with `grep -ril rounding skills integrations solo-sdd/specs` at the start of the run, which must find no skill about it).

1. `python3 sync.py push`, then `python3 sync.py status` → the laid-out `~/.claude/CLAUDE.md` and `spec-plan` hold the rule, no unexpected `drift`.
2. A subagent on `haiku` gets the laid-out section 14 of the global rules and the task "check that the tip calculator rounds money correctly" in a temporary copy of `examples/demo`; its answer is saved to the scratchpad → `python3 tests/stands/practitioner-techniques.py --grade <answer>` prints `list with sources: yes`, `ran named: yes`.
3. A subagent on `haiku` runs the laid-out `spec-plan` in a second copy (a git project, `process.analyze: off`) on "make the tip calculator round money the way a bookkeeper does" → `--grade-plan <copy>/solo-sdd/changes/<id>` prints `list in proposal: yes`, `task per item: yes`.
4. `python3 tests/test_skill_commands.py` on the repository → the persona test passes; the same test on a temporary copy of `skills/` with the line "You are an expert reviewer" added fails naming that file and line.

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
