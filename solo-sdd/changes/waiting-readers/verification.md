## Live Scenario

1. A `Lookup:` subagent on `haiku` runs the laid-out `context-resume` text on a copy of `tests/stands/next-up/project` whose `docs/waiting.md` has a `## Closed` row → its Blockers line names none of the closed rows.
2. A `Lookup:` subagent runs `blockers` on the same copy with one new blocker and returns the new `docs/waiting.md` → the row is in the first table.

## Needs

none

## Fallback

Not needed: the fixture is local.

## Result

<!-- Filled during apply: date, what was run, what was observed. -->

## Not Verified

<!-- Filled during apply: what stayed unproven and why. Write: nothing - if all proven. -->

## Decisions Without Owner

<!-- Filled during apply: choices made without asking, and new changes created for out-of-scope work. -->
