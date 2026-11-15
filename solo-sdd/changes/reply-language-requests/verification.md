## Live Scenario

A stand in a temporary home and a temporary git project with `solo-sdd/config` holding `reply.language: ru`: `python3 tests/stands/reply-language.py` lays the repository out with `python3 sync.py push` and `solo-sdd install --hooks` into the temporary home, runs the laid-out `~/.claude/hooks/work_hooks.py` of that home, and prints one `ok` or `FAIL` line per step and `reply-language: <n> of <n> checks passed`. The Russian texts are `\u` escapes in the stand.

1. `stop` with a transcript whose last user message is the Russian "translate into English" and an English final reply of 400 letters → no block.
2. The same transcript with a Russian question after the request → a block asking to rewrite the reply in Russian.
3. `stop` with a Russian reply that holds a 300-letter English draft in `:::writing … :::` → no block; the same English text without the block → a block.
4. `guard` with an `AskUserQuestion` call: the question "Roll out the change to the agent folders now?", options "Yes, roll out" and "Not now" with English descriptions → `permissionDecision` `deny`, the reason names Russian; the same window in Russian → no output.
5. The same English window with `reply.language: off` → no output.
6. The laid-out `~/.claude/settings.json` of the temporary home: the `guard` matcher holds `AskUserQuestion` once; a second `solo-sdd install --hooks` leaves the file unchanged.
7. The laid-out `~/.claude/CLAUDE.md` of the temporary home holds the new line 14 rule text.
8. All tests from the `## Commands` table of `AGENTS.md` → code 0.

## Needs

none

## Fallback

not needed.

## Result

<!-- Filled during apply: date, what was run, what was observed. -->

## Not Verified

<!-- Filled during apply: what stayed unproven and why. Write: nothing - if all proven. -->

## Decisions Without Owner

- analyze: the registration is an idempotence requirement → a Hypothesis test in task 1.4 — pass 3a.
- analyze: what counts as the user's message in a Claude Code transcript → text parts of user entries, tool results and hook feedback entries skipped, the form read from a real transcript — the hook's own block reasons must not count as a request.
