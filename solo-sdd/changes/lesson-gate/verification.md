## Live Scenario

The lesson stand, run as its `README.md` says, with the rules of the branch: `sync.py push` of the change's worktree into a temporary `HOME` gives the installed rules, and each prompt goes to a subagent of the running session (never `claude -p`) on the cheapest model `solo-sdd config get agents.test-model` prints, started in a fresh copy of `tests/stands/lesson-stand` with that `HOME`. The base is commit e262b7e (main when the change was planned), whose rules give the same prompts for comparison.

Before step 1, each fresh copy of the stand gets two UI string files, `ui/strings.json` (`{"save": "Save"}`) and `ui/labels.txt` (`Save changes`), committed with the stand.

1. Base rules, prompt "Never put an em dash into UI strings; fix it in the strings of this project." → `check.sh` shows a new `## Lessons` line; the reply holds no `Lesson gate:`.
2. Branch rules, the same prompt → `check.sh` shows the new line; the reply holds `Lesson gate:` naming a check of changed text files for the character and where it would run.
3. Branch rules, prompt "Name a function by what it returns, not by how it works." → a new `## Lessons` line; the reply holds no `Lesson gate:`.
4. Branch rules, in the copy after step 2, prompt "Add a check to check.sh that fails on an em dash in every text file of this project, and keep the lessons in order." → the dash line is gone from `## Lessons`, `LESSONS.md` holds its text under a `### <id>` heading with `Held by:`, the reply holds `Lesson held:`.
5. Branch rules, in a fresh copy after step 2, prompt "Add a check to check.sh that fails on an em dash in .json files only, and keep the lessons in order." → the dash line stays in `## Lessons`.
6. Branch rules, in the copy after step 4, prompt "No em dash in UI strings, remember." → `## Lessons` gets no new line, the reply has no `Lesson gate:` and names the check of step 4.
7. Branch rules, prompt "When you report a spec-next change, never print the archive path twice." → the reply holds `Lesson for solo-sdd:` and no `Lesson gate:`.

## Needs

- Seven subagent runs on `agents.test-model` (`haiku`) inside the session, one prompt each, no paid API calls.

## Fallback

If no subagent tool is available, steps 1 to 7 run in the session itself on the stand copy, and Not Verified says the runs were not independent of the author.

## Result

<!-- Filled during apply: date, what was run, what was observed. -->

## Not Verified

<!-- Filled during apply: what stayed unproven and why. Write: nothing - if all proven. -->

## Decisions Without Owner

<!-- Filled during apply: choices made without asking, and new changes created for out-of-scope work. -->

- plan (spec-analyze judge J5): no property test for the two rules: they are prose rules an agent follows, with no program to generate inputs for; Live Scenario steps 2 to 6 check them on the stand.
- plan (spec-analyze judge J12): the stand's own missing-await lesson is left to the agent's reading of "whose presence a program decides without judging intent"; a lint rule for unawaited calls exists in some languages, so either answer is defensible there.
- analyze: the first run's judge kept four HIGH (a README task with a `claude -p` path and an empty proof, a Live step that contradicted the partial scenario, no reader of `Held by:`); fixed by dropping the README task, a whole-class check in step 4 with a partial one in step 5, and the search for duplicates reading `Held by:` entries. The repeat run's five HIGH (the report form, the missing id, the `Lesson held:` line, the exception to Lesson from a correction or a fix, process lessons) are fixed in the delta and tasks 1.2 and 1.3.
