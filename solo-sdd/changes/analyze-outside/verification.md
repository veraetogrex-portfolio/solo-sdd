## Live Scenario

The stand `tests/stands/analyze-outside/` holds a fixture project with one change, `add-export`, built with four planted holes. `tests/stands/analyze-outside/planted.json` gives each hole its pass number and an identifying token: a requirement without a task (pass 1), a command that reads a user-given archive without a hostile input task (pass 2), two requirements true one by one that cannot hold together (pass 7a), a term that drifts between the proposal and the delta (pass 6). A finding matches a hole when its Pass and Where columns hold both. `tests/stands/analyze-outside.py --grade <file>` prints `found <x> of 4, unmatched keep <y>, tokens <t>`; the lead rereads every unmatched kept finding and records in `Result` whether the artifacts confirm it.

Every `--run` copies the fixture into a temporary git project and runs `claude -p "/spec-next add-export: stop after step 4a and print the step 4a report"` there on the subscription; `same-session` lays out the `spec-analyze` and `spec-next` texts of the base commit `8ce66d8` (read by `git show`, apart from the working folder), the other two the laid-out ones.

1. `python3 sync.py push`, then `python3 sync.py status` → the laid-out `spec-analyze`, `spec-plan`, `spec-next` and `~/.claude/CLAUDE.md` match the repository, no unexpected `drift`.
2. `python3 -m solo_sdd config get process.analyze-attackers` in the fixture project → `3` with the source `default`.
3. `python3 tests/stands/analyze-outside.py --run same-session` → the transcript has no `Analyze:`, `Attack:` or `Judge:` agent; the stand prints `same-session: found <x> of 4, unmatched keep <y>, tokens <t>`.
4. `python3 tests/stands/analyze-outside.py --run analyze` with `process.analyze-attackers: 0` in the fixture's `solo-sdd/config` → the transcript has one `Analyze: add-export` agent and one `Analyze: add-export 1 2 7 7a` repeat, no pass in the lead session; the report line starts with `Analyze: <n> findings, kept <n>, dropped 0`; the stand prints the `analyze:` grade line.
5. `python3 tests/stands/analyze-outside.py --run attack` with the default → the transcript has `Attack: add-export 1 2 3 3a`, `Attack: add-export 4 4a` and `Attack: add-export 5 6 7 7a 7b` on `haiku`, one `Judge: add-export`, no agent launched by an attacker or the judge, and `git status` of the fixture copy shows no edit before the lead's own edits; the report line matches `Analyze: <n> findings, kept <k>, dropped <d>; CRITICAL <c> · HIGH <h>, fixed <f>`; the stand prints the `attack:` grade line.
6. The stand prints the table of the three runs, and it goes into `Result` as is. Acceptance is the transcript structure and report lines of steps 3-5; an `attack` run that finds fewer planted holes than `same-session` is a `Not Verified` line and a new change, not a block.

## Needs

- Three `claude -p` runs on the owner's Claude subscription (8 model sessions in all: 1, 2 and 5, 3 of them on `haiku`), no paid API calls; a terminal logged in to Claude.

## Fallback

Without a logged-in `claude -p`: the lead session runs the three variants on the fixture copy itself as `Agent` calls with the same tags and models (`same-session` as a general subagent given the base commit texts), writes each findings file and grades it with `--grade <file>`; tokens are taken from the subagent transcripts, and `Not Verified` names the `claude -p` runs.

## Result

<!-- Filled during apply: date, what was run, what was observed. -->

## Not Verified

<!-- Filled during apply: what stayed unproven and why. Write: nothing - if all proven. -->

## Decisions Without Owner

<!-- Filled during apply: choices made without asking, and new changes created for out-of-scope work. -->

- analyze: a direct `/spec-analyze` call by the user → passes in place — the user asked for the analysis in that session; only `spec-plan` 7a and `spec-next` 4a, where the author checks its own work, go outside.
- analyze: the `same-session` baseline of the stand → the `spec-analyze` and `spec-next` texts of base commit `8ce66d8` read by `git show` — after this change the laid-out text no longer runs in session.
- analyze: overlap with the open change `lesson-merge-by-cause` (section 15 of `global/AGENTS.md`, `tests/test_skill_commands.py`) → it goes into Depends On, which orders it before the whole chain of this plan.
