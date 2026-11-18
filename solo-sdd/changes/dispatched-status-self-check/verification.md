## Live Scenario

The self-check is a step of the skill text that the orchestrator follows, so the live check runs the real `sdd-dispatch.py accept` on the two forms of a status from the settings-ci-wait run, and checks that the deployed skill and prompt carry the step.

1. `python3 tests/stands/dispatched-status-self-check.py` → the stand builds a temporary worktree with a change archive whose `## Live Scenario` names `python3 stand.py` (prints `demo: 4 of 4 checks passed`). It runs the repository's `global/sdd_dispatch.py accept` on a status whose `LIVE` says `-> all four checks pass` and sees code 1 with a `LIVE:` mismatch line.
2. The same stand runs `accept` on the status with the printed line copied verbatim, `-> demo: 4 of 4 checks passed`, and sees `status matches`.
3. The stand reads `skills/spec-next/SKILL.md` (with its step files) and `skills/spec-dispatch/orchestrator-prompt.md` and finds the self-check step and the verbatim `LIVE` rule. It prints `dispatched-status-self-check: 3 of 3 checks passed`.
4. `HOME=<temporary home> python3 sync.py push` → `all laid out`, exit 0, and the laid-out `~/.claude/skills/spec-next/SKILL.md` and `~/.claude/skills/spec-dispatch/orchestrator-prompt.md` of that home carry the self-check step and the verbatim `LIVE` rule. The real agent folders are laid out only after merge, as the Delivery section of `AGENTS.md` says.

## Needs

none

## Fallback

Not needed: the stand runs locally without access or paid calls.

## Result

<!-- Filled during apply: date, what was run, what was observed. -->

## Not Verified

<!-- Filled during apply: what stayed unproven and why. Write: nothing - if all proven. -->

## Decisions Without Owner

<!-- Filled during apply: choices made without asking, and new changes created for out-of-scope work. -->

- analyze: step 4 ran `python3 sync.py push` on the real agent folders from the change's worktree, a prod action before merge → a temporary `HOME`, as the archived settings-* changes check the laid-out text — the real push stays the separate delivery step.
- analyze: `accept` re-runs the `LIVE` stand and `VALIDATE`, so the self-check costs one more stand run per handback → accepted: one local run is cheaper than a `SendMessage` round trip and a second acceptance; no shortcut that skips the run, since a stated line must be checked against real output.
