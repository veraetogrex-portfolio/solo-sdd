## Live Scenario

1. In a temporary git project with `solo-sdd/` and no `process.review-rounds` in `solo-sdd/config`: `python3 -m solo_sdd config get process.review-rounds` → `5` and `source: default`.
2. `python3 scripts/sync_blocks.py --check` → no output, code 0; `grep -rn '"process.review-rounds"' solo_sdd global` → every line has `"5"`.
3. `python3 sync.py push` into a temporary home, then the laid-out `~/.claude/skills/spec-next/SKILL.md` and `~/.local/share/solo-sdd/ALGORITHM.md` of that home → both name default 5, `docs/stop-conditions.md` names the setting and the extra round, the fallback 5, the extra round only for findings in the lines of the last rework and no second extra round.
4. `python3 tests/stands/settings-tui.py` → it passes and lists `process.review-rounds 5 default`.
5. All tests from the `## Commands` table of `AGENTS.md` → code 0.

## Needs

none

## Fallback

not needed.

## Result

<!-- Filled during apply: date, what was run, what was observed. -->

## Not Verified

<!-- Filled during apply: what stayed unproven and why. Write: nothing - if all proven. -->

## Decisions Without Owner

- analyze: "the lines the last rework changed" had no measure → the finding's places against `git diff` of the rework before the last round — the agent can compute it.
- analyze: with a limit of 1 there is no rework before the last round → no extra round — the extra round is for findings on a fix.
- analyze: `docs/stop-conditions.md` still said three rounds → in Impact and task 1.4 — requirement of readme-content that every stop condition is listed with its file.
- analyze: no property test → the extra round is a rule the agent follows, not code; a Hypothesis test has nothing to run — pass 3a does not apply.
