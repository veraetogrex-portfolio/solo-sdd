## Live Scenario

1. `python3 tests/stands/settings-stop-hooks.py` → the stand runs the real `global/work_hooks.py stop` on hook input. A new step makes a repository with a tracked `solo-sdd/config` (`hooks.stop.open-pr: on`) and a worktree that commits `hooks.stop.open-pr: off`. It gives a fake `gh` that shows an open PR and a transcript with `git push`.
2. With `cwd` in the worktree the stop is not blocked. On the previous code it is blocked with "is open and not merged".
3. A second repository that ignores `solo-sdd/config` (`info/exclude`), with the main checkout's file at `delivery.merge-by: human` and a worktree that has no such file: the stop is not blocked (the fallback; it passes on the previous code too and guards the fallback against the fix).
4. The earlier steps still pass, and the stand prints its summary line with every check passed.

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

- analyze: the scenario of a worktree without a config file sat in a repository that tracks `solo-sdd/config`, where every worktree checks the file out → that case is a repository that ignores the file, kept only in the main checkout — the only way a worktree has none.
- analyze: a worktree whose committed file lacks `hooks.stop.open-pr` while the main checkout's file says `off` → the worktree's file applies, its default `on` included — the file of the checked branch is the source, as the requirement says, no key-by-key merge.
