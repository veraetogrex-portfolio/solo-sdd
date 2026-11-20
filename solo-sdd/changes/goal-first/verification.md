## Live Scenario

`tests/stands/goal-first.py` copies `examples/demo` into a temporary folder, runs `git init` there with one commit and `delivery.mode: local`, sets `process.analyze: off` in the copy's `solo-sdd/config` (the stand grades planning, not the cross-check), makes `test_usual_bill` of `tests/test_tip.py` slow (a sleep of 2 s), and writes the request "remove the tests test_usual_bill and test_not_a_number"; `--grade <copy> <report>` reads the created change and the saved report.

1. `python3 sync.py push`, then `python3 sync.py status` → the laid-out `spec-plan` and `~/.claude/CLAUDE.md` hold the rule, no unexpected `drift`.
2. A subagent on `haiku` runs the laid-out `spec-plan` in the copy on the request and saves its report → `python3 tests/stands/goal-first.py --grade <copy> <report>` prints `goal in Why: yes`, `check with a number: yes`, `inferred marked: yes`, `both steps have tasks: yes`, `proposal names test_not_a_number: yes`.
3. A subagent on `haiku` gets the laid-out section 6 of the global rules and "rename the tests test_usual_bill and test_not_a_number" in a second copy, outside `spec-plan` → its report opens with a goal and a check marked inferred; `--grade-report <report>` prints `goal first: yes`.

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
