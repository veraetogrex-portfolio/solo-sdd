## Live Scenario

1. `python3 tests/stands/setup-links-exclude.py` → the stand builds a temporary `MAIN` whose branch tracks `app/keep.txt`, with an ignored `app/node_modules/p/i.js` and a `.venv` folder, and a worktree of a new branch. It makes the worktree root read-only (`app/` stays writable), so `setup` links `app/node_modules` and then fails on the root `.venv` link with a permission error. It runs the repository's `global/sdd_worktree.py setup` and sees code 1. (The stand is skipped with a line saying so when it runs as root, where the mode does not stop a write.)
2. `info/exclude` of the shared git directory has the line `node_modules`, and `git -C <WORKTREE> status --short` does not list `app/node_modules`. On the previous code it lists `?? app/node_modules/`.
3. The stand gives the root its mode back, and `global/sdd_worktree.py remove` is not refused for the links. The stand prints `setup-links-exclude: 3 of 3 checks passed`.

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

- analyze: the stand made `.venv` fail with a file already at `WORKTREE/.venv`, but the loop skips a destination that exists (`os.path.lexists(dst)` → `continue`), so `setup` would end with code 0 and prove nothing → a read-only worktree root with `node_modules` under a writable `app/`: `find_links` gives `node_modules` items first, so `app/node_modules` is made and the root `.venv` symlink raises — a real failure of the real `os.symlink`, no double of the module under test.
