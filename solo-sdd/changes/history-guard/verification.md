## Live Scenario

The real hook as Claude Code starts it: `python3 global/work_hooks.py guard` with a PreToolUse JSON on stdin (`tool_name: Bash`, the command, `cwd` a temporary git repository with one commit and a bare remote), the way `entry` in `tests/test_work_hooks.py` runs it; an empty answer means the command passes, a `deny` answer prints its reason.

The base is commit e262b7e (main when the change was planned): its hook runs from a temporary worktree of that commit (`git worktree add --detach "${TMPDIR:-/tmp}/wt-base-e262b7e" e262b7e`, removed after); the branch hook runs from the change's own worktree.

1. Steps 1-3 run as one stand, `python3 tests/stands/history-guard.py`, which builds the repository, the remote and the base worktree and removes them; its last line is the summary. On the base commit, `git push --force origin main` and `git reset --hard HEAD` → no answer (they pass).
2. On the branch, the same two commands → `deny`; the reasons name the rule, a new commit and `git stash`.
3. On the branch, `git commit -m "never git push --force"`, `python3 sync.py push --force` and `git push origin main` → no answer.
4. In a Claude Code session after `sync.py push` of the merged change (the delivery's layout step), in a temporary repository with a bare remote: ask the agent to run `git push --force origin main` → the Bash call is refused by the hook (the evidence is the hook's deny line in the session transcript; an agent that declines before the call is "not run") and the remote branch keeps its commit (`git ls-remote` shows the same hash before and after).

## Needs

- Step 4: the layout of the merged change on the owner's machine (`sync.py push`) and one Claude Code session there.

## Fallback

Step 4 needs the layout, a prod action after merge: before it the hook from the branch is run by its entry point (steps 1-3), and Not Verified names step 4 if the layout has not happened, with a line in the first table of `docs/waiting.md`.

## Result

2026-11-27, `python3 tests/stands/history-guard.py` from the worktree root (git 2.54.0, /usr/bin/python3):

- step 1, base e262b7e: `git push --force origin main` and `git reset --hard HEAD` pass;
- step 2, branch: both get `deny`, the reason names the rule, a new commit and `git stash`;
- step 3, branch: `git commit -m "never git push --force"`, `python3 sync.py push --force` and `git push origin main` pass;
- no `errors.log` line; summary `history-guard stand: 4 of 4 steps ok`.

Suite: `python3 tests/run.py --jobs 5 --tier slow` gives `files: 42, failed: 0`; lint prints nothing; `solo-sdd validate --all` gives 0 errors.

## Not Verified

- Step 4 (a Claude Code session with the laid-out hook refusing `git push --force origin main`): it needs `sync.py push` of the merged change, a prod action after merge; by the Fallback steps 1-3 ran on the hook's entry point, and a row is in the first table of `docs/waiting.md`.

## Decisions Without Owner

<!-- Filled during apply: choices made without asking, and new changes created for out-of-scope work. -->

- analyze: the first run's judge kept five HIGH (no hostile-input task, no property for `--hard`, an unnamed audit test, a bypass list given only by reference, git's abbreviated options); all fixed in the delta and tasks 1.2, 1.4, 1.6 and 1.7. Kept MEDIUM `--force-if-includes` without a row, the undefined generator slots, the test name, the `python3` heredoc and the Needs of step 4 are fixed too.
- analyze (repeat): options follow git's own parsing: a force letter after `-o` in a cluster is its value, and `--hard` after `--` is a path; both pass.
- plan: `--force-with-lease` counts as a forced push: the global rule says "No `--force`" and a lease still rewrites the remote branch.
- analyze (spec-next): the judge kept 11 of 17 findings, CRITICAL 1 and HIGH 2. Fixed: both refusal requirements now say "by its plain forms" and let the forms of Known bypasses pass (CRITICAL); the slow shape of broken input is named (backslash-newline lines, deep nesting) and `strip_heredocs` joins continuation lines linearly (HIGH); the unterminated heredoc row is `cat <<EOF; git push -f`, refused, while a body line of a text reader stays text (HIGH). Also fixed: valued wrapper options, a configured `+` refspec and a git alias are named bypasses; the version claims were probed on git 2.54.0 (`--force-w` and `--force-with` forced an update, `--force-i` did not, `--f` to `--forc` are ambiguous and git refuses them, `--h`, `--ha`, `--har` reset hard); the property test names both requirements and has a broken-input sibling; the `ship` hook cell becomes empty; Live step 4 names its evidence.
- implementation: a word is a force when it (before `=`) is a prefix of `--force`, `--force-with-lease` or `--force-if-includes`, at least `--f` long: an ambiguous prefix git refuses anyway, so refusing it costs nothing; no full option table of `git push` is kept, only the value-taking names, which a test checks against `git push -h`.
- analyze (repeat, spec-next): a `+` refspec after `--` still forces (git 2.54 printed `(forced update)` for `git push <remote> -- +HEAD:refs/heads/main`), so it is refused and only an option form after `--` passes; the backslash-newline bypass is the one between `$` and `(`, as the merge guard names it; the proposal lists every pinned bypass and the known false refusal.
- implementation: the deep nesting row is 5,000 levels, not 50,000: the guard as a whole took 103 s on 50,000 (1.4 s on 5,000), spent in a regex search of `guard_secrets_bash`, which this change does not touch (the history reader itself is linear there); the slow secret-check shape is left for a change of its own and the 10-second entry timeout refuses it meanwhile.
- implementation: `strip_heredocs` lies in the `shell` block that `scripts/sync_blocks.py` copies from `global/work_hooks.py` into `global/process-guard.py`, so the linear join reaches `process-guard` by that copy; its behaviour (what it refuses) is unchanged, so Out of Scope still holds, and `global/process-guard.py` is added to Impact.
- review round 1: three Important findings were reader gaps shared with the merge guard (the reviewer's Pre-existing P1): a leading `(`, `{` or `!` that `cmd_start` strips in place hid the program from the matcher, a redirection before the program (`>/dev/null`, `2>&1`) stopped the program search, and `git --attr-source` and `--config-env` take the next word as their value. The first two are fixed once in `gh_merges`, so the merge guard refuses `( gh pr merge 5 )` and `>/dev/null gh pr merge 5` too, pinned in `DirectMerge`; this narrows no requirement of the merge guard (its plain forms gain refusals). The two git options go only into the history reader's set (`git_sub` takes the set as an argument): in the shared `GIT_GLOBAL_VALUED` they closed the pinned worktree-guard known pass `git --config-env a.b=C worktree $A /tmp/x`, a requirement of another change.
- review round 1, other findings: the escape `\;` and a missing space in the test table are fixed (Nit); `git push --force --no-force` and `git reset --pathspec-from-file --hard` are refused although git does not force there: harmless extra refusals, kept (Nit); the docs rows and `test_ship_push_is_a_code_gate` are what task 1.7 asks for (the skill-ablation audit rule: a held gate is `gate (code)` and leaves Gates a hook could hold), and `test_forced_push_refused_git_option_names` is the drift check of the option names against `git push -h` the analyze judge asked for: both kept.
- review round 2: the redirection skip dropped a whole quoted `-c` or `eval` string starting with `>` (shlex has removed its quotes), so `bash -c ">x; git push -f"` and `eval '>x; gh pr merge 5'` passed: a word with whitespace is now never a redirection, and these rows are pinned in `HistoryGuard` and `DirectMerge` (Important, fixed). Kept: a quoted argument that is exactly an operator (`gh api -H ">" …`) is still read as a redirection and drops the next word, since shlex leaves no trace of its quotes (Nit, contrived); `>| out git push -f` passes because `split_cmd` splits at the `|` (Pre-existing).
- review round 3: the whitespace rule of round 2 was a second fix of one cause, quotes lost before the redirection was decided: `>'my out.log' git push -f` and `eval '>x;git' push -f` passed. `gh_merges` now splits a command into words with their quotes (`shell_words`), drops a word only when it starts with an unquoted operator, and unquotes each kept word after; this also closes the round-2 Nit `gh api -H '>' …`. The rows are pinned in `HistoryGuard` and `DirectMerge`.
