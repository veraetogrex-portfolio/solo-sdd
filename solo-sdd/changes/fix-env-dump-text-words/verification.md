## Live Scenario

The real hook as Claude Code starts it: `python3 global/work_hooks.py guard` with a PreToolUse JSON on stdin (`tool_name: Bash`, the command, `cwd` the repository); an empty answer means the command passes, a `deny` answer prints its reason. The commands are the ones of the reproduction, as the sessions ran them.

1. On the base commit 286817e (its hook run as `python3 <worktree>/global/work_hooks.py guard` from a temporary worktree of that commit), `grep -n "secret\|printenv\|env |echo \$" skills/debug-profile/SKILL.md`, `grep -n "foo\|env\[" global/sdd_eval.py`, `[ -n "$(git status --short)" ] && echo yes; (cd /tmp && env -i HOME=$HOME PATH=/usr/bin:/bin python3 report.py < /dev/null | tail -4)` and `echo "$(date)"; env X=1 python3 -V` → each `deny`, "The command prints the whole environment or a secret".
2. On the branch, the same four commands and `echo "$(date)"; env -u HOME python3 -V` → no answer (each passes).
3. On the branch, `export -p` and every command of the scenarios Dumps still refused and Other programs' scripts are not text → each `deny` with the same reason.
4. In a Claude Code session after `sync.py push` of the merged change (the delivery's layout step): the first `grep` of step 1 run through the Bash tool from the repository prints its matching lines instead of the hook refusal.

## Needs

none

## Fallback

Step 4 needs the layout, a prod action after merge: before it the hook from the branch is run by its entry point (steps 1-3), and Not Verified names step 4 if the layout has not happened, with a line in the first table of `docs/waiting.md`.

## Result

<!-- Filled during apply: date, what was run, what was observed. -->

## Not Verified

<!-- Filled during apply: what stayed unproven and why. Write: nothing - if all proven. -->

## Decisions Without Owner

<!-- Filled during apply: choices made without asking, and new changes created for out-of-scope work. -->

- plan (spec-analyze judge 10): the exemption covers the quoted arguments of `grep` and `rg` only, not `sed` and `awk` as the owner's item D said: GNU sed's `e` and awk's `getline`, `| "cmd"` and `system(` run programs from a quoted script, and every refusal of the week was a `grep`.
- plan (analyze repeat 2, 3): `env` counts only at a command position, so a heredoc text `guard env dumps` stays refused; `grep` after `env` or a wrapper is still `grep`.
- plan (analyze repeat 6): the plain-path holes (`env -u X printenv`, `env -C /tmp printenv`, `awk 'BEGIN{system("env")}'`) are older than this change and go to a change of their own, proposed in the plan report.
- plan (judge 12): only the `env` word, its options with their values, its assignments and its program word are exempt; a dump word after them still counts.
