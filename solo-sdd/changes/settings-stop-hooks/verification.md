## Live Scenario

Feed `global/work_hooks.py` hook events (Stop, and the `tasks.md` edit of step 5) in a temporary git project with a temporary home:
1. An uncommitted session edit, no config → blocked for uncommitted edits; with `hooks.stop.uncommitted: off` → not blocked.
2. An edited `app.css` without a browser check → blocked; with `hooks.stop.ui-check: off` → not blocked.
3. `ui.extensions: .html, .jinja` and an edited `page.jinja` → blocked for the interface check.
4. A broken config line and an uncommitted edit → blocked, the temporary home's `errors.log` names the line.
5. A tick in `tasks.md` with `hooks.auto-claim: off` → no `CLAIM` file.
6. `hooks.stop.open-pr: on`, `delivery.merge-by: human`, a pushed branch and a fake `gh` reporting an open PR → not blocked for the open PR; with `delivery.merge-by: agent` → blocked.

All in one call: `python3 tests/stands/settings-stop-hooks.py` → `6 of 6 checks passed`.

## Needs

none

## Fallback

not needed.

## Result

<!-- Filled during apply: date, what was run, what was observed. -->

## Not Verified

<!-- Filled during apply: what stayed unproven and why. Write: nothing - if all proven. -->

## Decisions Without Owner

- analyze: `hooks.stop.open-pr: on` together with `delivery.merge-by: human`, which today turns the gate off → the gate stays off under a human merge whatever its switch — an open PR is the expected end when a person merges; the switch can only turn the gate off further.
- analyze: a session edits several repositories and the hook loops by root → each gate reads the settings of the repository it checks (each edited root, the change's repository, the session's repository for the open PR) — one project's switch must not silence another project's gate.
- analyze: `hooks.auto-claim: off` and the refusals of the same hook → only the creation of `CLAIM` stops; a foreign `CLAIM` and a `WAITING` are still refused — they protect another agent's work.
- analyze: `ui.extensions` and `ui.widths` had the generic list kind, which accepts `wide` and prints "branch names" in `config describe` → extensions are `.` plus letters or digits, widths whole numbers from 1, anything else refused with exit 1; the extension default is named in the spec — a default worded as "the current list" cannot be tested once the hook reads the setting.
- analyze: `project-init` step 5a also reads the extension list → it is a named consumer of `ui.extensions`.
