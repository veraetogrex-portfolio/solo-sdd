## Live Scenario

1. `python3 tests/stands/settings-stop-hooks.py` → the stand runs the real `global/work_hooks.py stop` on hook input. A new step makes a repository that ignores `solo-sdd/config`, with `hooks.stop.uncommitted: off` in the main checkout, and a plain worktree without the file that holds an uncommitted edit. With `cwd` in that worktree the stop is not blocked; on the previous code it is blocked with "has uncommitted edits".
2. The same step with `hooks.stop.ui-check: off` and an edited `app.css` is not blocked for the interface check.
3. The earlier steps still pass, and the stand prints its summary line with every check passed.

## Needs

none

## Fallback

Not needed: the scenario runs locally without access or paid calls.

## Result

<!-- Filled during apply: date, what was run, what was observed. -->

## Not Verified

<!-- Filled during apply: what stayed unproven and why. Write: nothing - if all proven. -->

## Decisions Without Owner

<!-- Filled during apply: choices made without asking, and new changes created for out-of-scope work. -->

- analyze: `main_checkout` returns the main checkout's git root, while the unarchived gate reads `change_project(cdir)`, which can be a folder below the root → the helper keeps the folder's path relative to its git root in the main checkout; reading the main's root was rejected: it would read another project's file.
- analyze: task 1.2 placed the edits by line numbers → by function and gate names.
