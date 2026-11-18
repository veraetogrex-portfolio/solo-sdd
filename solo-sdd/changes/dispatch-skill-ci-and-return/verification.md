## Live Scenario

1. `python3 tests/stands/dispatch-skill-ci-and-return.py` → the stand lays the repository out into a temporary HOME with `sync.py push`, reads the laid-out `~/.claude/skills/ship/SKILL.md` and `~/.claude/skills/spec-dispatch/merge.md` (with their step files), and finds the `checks not read` step in both. The step names fixing gh, forbids the rerun and the empty commit, and names the outcome of a repeated `checks not read`.
2. It builds a temporary main repository and worktree where WORKTREE holds an ignored `solo-sdd/config` with the text `mine` and its branch has a commit of its own, then commits `solo-sdd/config` on main with `git add -f`. It runs the check and merge commands copied from the laid-out Return on conflict text with the laid-out `~/.local/bin/sdd-pr.py`. The check prints `merge would overwrite ignored files in WORKTREE: solo-sdd/config` with code 1, no merge runs, and the file still holds `mine`. On the previous text (a plain merge) the file takes main's text; `git merge --no-overwrite-ignore` gives main's text too.
3. The stand prints `dispatch-skill-ci-and-return: 2 of 2 checks passed`.

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

- analyze: the planned `git merge --no-overwrite-ignore` was probed in a scratch repository with git 2.54: it refuses a fast-forward, but a merge of a branch with its own commit replaced the ignored file, code 0 (`ort` and `-s resolve` alike), as the archive of fix-worktree-ignored-overwrite already noted → a read-only `sdd-pr.py overwrites` over the existing `untracked_written` guard, run before the plain merge — a shell comparison in the skill text was rejected: it would miss the directory, nested-repository and case forms the helper already handles.
- analyze: the new check made the Merge conflict return text longer than 500 characters → a separate ADDED requirement Return keeps worktree ignored files; Merge conflict return stays as in the main spec. The code 3 return of Red check after merge uses "the same branch update", so it gets the check too.
- analyze: the stand fixture gives WORKTREE's branch a commit of its own, the only form where the native flag fails.
- analyze: `/ship`'s own `git merge origin/<main branch>` on `merge` code 5 has the same overwrite class → named in Out of Scope as a separate change, not widened here.
- analyze: the repeated `checks not read` outcome had no scenario → scenario gh still cannot read the checks.
