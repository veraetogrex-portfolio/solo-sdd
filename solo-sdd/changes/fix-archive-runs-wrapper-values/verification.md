## Live Scenario

The stand `tests/stands/archive-run-words.py` drives a hook by its entry point (`python3 <hook> guard` with a PreToolUse JSON) from a script file: step 1 a transcript where the session edited `src/app.py` and ran no `Review:` agent (the reason names `src/app.py`), step 2 a change with a foreign CLAIM (the reason has `taken by another agent`). Its `FORMS` hold the 7 earlier forms and the 10 of the scenario Valued options of other wrappers; its `TEXT` the 2 earlier rows and the 3 of the scenario An option value is not the program.

1. Base, before the deployment: the deployed copy `~/.claude/hooks/work_hooks.py` is main b6844a4 (`python3 sync.py status`), whose `archive_runs` and `wrapper_values_cut` are those of 9f138c8. From the branch's repository root: `SOLO_SDD_HOOK="$HOME/.claude/hooks/work_hooks.py" python3 tests/stands/archive-run-words.py` → `FAILED` lines for the new forms except `npx -p x solo-sdd archive add-words` (both steps) and for `npx -p solo-sdd archive add-words`, `npx --package solo-sdd archive add-words` and `sudo -Hu solo-sdd archive add-words` (refused today); exit 1.
2. Deployment after the merge: `python3 sync.py push` from the repository root on main, then `python3 sync.py status` → `work_hooks.py` deployed with no `drift`.
3. After the deployment, the same command → every line `ok`, the last line `archive-run-words: 39 of 39 checks passed`, exit 0.

## Needs

none

## Fallback

Nothing to replace: the scenario needs no access beyond this computer; `sync.py push` is done without a question by the owner's standing rule for ready changes.

## Result

<!-- Filled during apply: date, what was run, what was observed. -->

## Not Verified

<!-- Filled during apply: what stayed unproven and why. Write: nothing - if all proven. -->

## Decisions Without Owner

<!-- Filled during apply: choices made without asking, and new changes created for out-of-scope work. -->
