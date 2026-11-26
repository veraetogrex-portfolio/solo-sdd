## Live Scenario

0. Without models: `python3 tests/stands/lesson-gate.py` from the repository root. It runs `sync.py push --global-rules` of this tree into a temporary `HOME` and checks that the installed `~/.claude/CLAUDE.md` and `~/.codex/AGENTS.md` (section 15) name `Lesson gate:`, `Held by:` and `Lesson held:` and the installed `spec-next` names `Lesson gate:` and `Lesson held:`; that `global/AGENTS.md` of base commit e262b7e (main when the change was planned) names none of them; and that a copy of `tests/stands/lesson-stand` with the two UI string files `ui/strings.json` (`{"save": "Save"}`) and `ui/labels.txt` (`Save changes`) committed in its own git prints `## Lessons: missing` from `check.sh` and passes no test until a model run adds one. With `--prepare <dir>` it leaves in `<dir>` the `HOME`, the base rules and the fresh copies `c1` to `c5` for the model steps; the caller removes `<dir>`. The last line is `SUMMARY: all steps passed`.

The model steps: each prompt goes to an agent with the rules of step 0 (the base rules for step 1, the installed branch rules for the rest): a subagent loads the session's own installed rules, so its prompt carries section 15 of the named rules, which replaces the section 15 it loaded; started in the named copy of step 0, on the cheapest model `solo-sdd config get agents.test-model` prints; never `claude -p`. Of the stand's `README.md` only the copy block applies. A test the agent adds goes into the stand's suite (`python3 -m unittest -v`), which runs on every change of the stand.

1. `c1`, base rules, prompt "Never put an em dash into UI strings; fix it in the strings of this project." → `check.sh` shows a new `## Lessons` line; the reply holds no `Lesson gate:`.
2. `c2`, branch rules, the same prompt → `check.sh` shows the new line; the reply holds `Lesson gate:` naming a check of the UI string files for the character and where it would run. The same in `c3`.
3. `c4`, branch rules, prompt "Name a function by what it returns, not by how it works." → a new `## Lessons` line; the reply holds no `Lesson gate:`.
4. `c2` after step 2, prompt "Add a test to this project's suite that fails on an em dash in every file under ui/, and keep the lessons in order." → the dash line is gone from `## Lessons`, `LESSONS.md` holds its text under a `### <id>` heading with `Held by:` naming the test and the suite, the reply holds `Lesson held:`.
5. `c3` after step 2, prompt "Add a test to this project's suite that fails on an em dash in the .json files under ui/ only, and keep the lessons in order." → the dash line stays in `## Lessons`.
6. `c2` after step 4, prompt "No em dash in UI strings, remember." → `## Lessons` gets no new line, the reply has no `Lesson gate:` and holds `Lesson held:` naming the test of step 4.
7. `c5`, branch rules, prompt "When you report a spec-next change, never print the archive path twice." → the reply holds `Lesson for solo-sdd:` and no `Lesson gate:`.

## Needs

- Eight subagent runs on `agents.test-model` (`haiku`) inside the session, one prompt each, no paid API calls. Under the dispatcher the hook refuses an orchestrator's untagged subagents, so there the Fallback runs.

## Fallback

If no subagent tool is available, or the hook refuses the runs, steps 1 to 7 run in the session itself on the copies of step 0 with the rules of step 0, and Not Verified says the runs were not independent of the author.

## Result

<!-- Filled during apply: date, what was run, what was observed. -->

## Not Verified

<!-- Filled during apply: what stayed unproven and why. Write: nothing - if all proven. -->

## Decisions Without Owner

<!-- Filled during apply: choices made without asking, and new changes created for out-of-scope work. -->

- plan (spec-analyze judge J5): no property test for the two rules: they are prose rules an agent follows, with no program to generate inputs for; Live Scenario steps 2 to 6 check them on the stand.
- plan (spec-analyze judge J12): the stand's own missing-await lesson is left to the agent's reading of "whose presence a program decides without judging intent"; a lint rule for unawaited calls exists in some languages, so either answer is defensible there.
- analyze: the first run's judge kept four HIGH (a README task with a `claude -p` path and an empty proof, a Live step that contradicted the partial scenario, no reader of `Held by:`); fixed by dropping the README task, a whole-class check in step 4 with a partial one in step 5, and the search for duplicates reading `Held by:` entries. The repeat run's five HIGH (the report form, the missing id, the `Lesson held:` line, the exception to Lesson from a correction or a fix, process lessons) are fixed in the delta and tasks 1.2 and 1.3.
- analyze (outside run at spec-next, judge J1, HIGH): task 1.1 named four kinds of mechanical cause, the requirement six → the task names the six of the requirement.
- analyze (judge J2, HIGH): `Held by: <check>` fixed neither the form nor where the check runs → the requirement takes only a check that runs on every change (a hook, CI or the test suite), the entry is `Held by: <check command or file> — <where it runs>`, and a check nothing runs keeps the line; Live steps 4 and 5 add a test to the stand's suite instead of a line of the hand-run `check.sh`.
- analyze (judge J5, J6, MEDIUM): the exception to Lesson from a correction or a fix and to Gate stood only inside Lesson held by a check, and no requirement made the search for duplicates read `Held by:` → a separate ADDED requirement Held lesson not written again names both exceptions and the search; kept ADDED rather than MODIFIED because both main requirements stay true for every lesson no entry covers, and section 15 writes the exception in the bullet of the search, where the agent reads it.
- analyze (judge J3, J9, J10, MEDIUM/LOW): copy states of the Live steps, the README reference and "every text file" → named copies `c1` to `c5` (eight runs), only the README copy block, files under `ui/`.
- analyze (judge J4, MEDIUM): the clause "where edits are not allowed, nothing is removed" had no check → task 1.2 asserts it.
- analyze (judge J8, MEDIUM): `doctor` `ok rules-size` does not read `global/AGENTS.md` of the tree → task 1.3 measures `wc -c global/AGENTS.md`.
- analyze (judge J7, MEDIUM): kept by the judge, not fixed → a check later removed or narrowed leaves its `Held by:` lesson out of `## Lessons`; restoring the line is a rule about removing checks, outside this change's What Changes.
- analyze (repeat, A1-A4, HIGH): how the named rules reach a model run, a check added outside a change, the form of the report line for a held lesson repeated, and `lessons.write: off` → the prompt carries section 15 of the named rules; the requirement reads "a change or an edit"; the repeated held lesson gives `Lesson held: <lesson> -> <check>`, a line that starts with `Lesson` and so reaches the dispatcher's `Lessons:`; `lessons.write: off` and forbidden edits remove nothing and give no `Lesson held:`. A6 (MEDIUM): What Changes names the `Held by:` form and `Lesson held:`. A5 (MEDIUM): not fixed, kept ADDED as recorded for J5 and J6.
