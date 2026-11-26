# Proposal

## Why

The global rules forbid two git commands in one line, `global/AGENTS.md` section 13: "No `--force` and no `git reset --hard`." Nothing enforces it. `docs/skills-audit.md` already lists it under "Gates a hook could hold" (`ship`, step 6 Push: "a Bash guard refusing `git push --force` and `-f`"), and no change plans it. A forced push rewrites the remote history of a branch another worktree or orchestrator may stand on; a hard reset drops uncommitted work in the one working folder the rules keep per project. Both are the kind of action the chief-of-staff-kit (https://github.com/skyremote/chief-of-staff-kit, `templates/hooks/gate-protected-push.sh`) and the skills of Matt Pocock (https://github.com/mattpocock/skills, `skills/misc/git-guardrails-claude-code`) move out of prose into a PreToolUse hook, because a hook runs every time and a rule in the text gets forgotten.

Their scripts match substrings (`grep -qE "push --force"`), which refuses `git commit -m "never push --force"` and `python3 sync.py push --force`. The `guard` hook already reads a command by the words the shell will run for the merge guard (`gh_merges`, `guard_merge` in `global/work_hooks.py`): messages, search patterns and heredoc bodies for text readers are text, not commands. The new guard uses the same reader.

## What Changes

- `guard` refuses a Bash command that runs `git push` with `--force`, `-f` (alone or in a cluster such as `-fu`), `--force-with-lease`, `--force-if-includes`, an unambiguous prefix git reads as one of them (git 2.43 forced an update on `--force-w`) or a refspec that starts with `+`, and a command that runs `git reset` with `--hard` or its prefix (`--har` reset hard on git 2.43), in any project and from any caller, with a reason that names the rule and the safe way: a new commit and a normal push, or `git stash` / `git restore <path>`.
- It reads words the way the merge guard does: past `git -C <path>` and other global options (`git_sub`), wrappers, assignments, `eval`, a shell's `-c` string and substitutions up to depth 3; a commit or tag message, a search pattern and a heredoc body for a text program are not commands.
- `git push origin main`, `git push --delete origin x`, `git reset --soft HEAD~1`, `git worktree remove --force x` and `python3 sync.py push --force` pass.
- Known bypasses are listed by name and pinned by a test that they pass: `xargs`, `find -exec`, a shell function, `A=(1 2) bash -c` and `A=(1 2) eval`, substitutions deeper than 3, a git alias, and a `python3` or `node` heredoc body that runs git. Branch protection on the remote stays the boundary for a push; for a hard reset nothing else stands in the way.
- Broken input (an unclosed quote or substitution, a very long command) is refused within the hook's time and raises nothing, since an exception in `guard` lets the call through.
- `docs/hooks.md` lists the new refusal; the `ship` row of `docs/skills-audit.md` becomes `gate (code)` and leaves "Gates a hook could hold".

## Capabilities

### New Capabilities
- `history-guard`: the `guard` hook refuses the forced push and the hard reset the global rules forbid.

### Modified Capabilities

## Impact

- `global/work_hooks.py`
- `tests/test_work_hooks.py`
- `tests/test_skill_commands.py`
- `docs/hooks.md`
- `docs/skills-audit.md`

## Out of Scope

- `git clean -f`, `git branch -D`, `git checkout .`, `git restore .` and `git push --mirror`, which the scripts above also refuse: the global rules do not forbid them, and `spec-plan` itself runs `git branch -D plan/<id>` after a merge.
- `process-guard.py`, which stays about process control only.
- The text of `global/AGENTS.md`: the rule line stays as it is.
- Neighbouring changes of this plan: `codex-user-only-skills`, `guard-fails-closed`, `lesson-gate`.

## Depends On

none

## Source

The owner, 2026-11-26, on the comparison of solo-sdd with mattpocock/skills, skyremote/chief-of-staff-kit and davidondrej/skills (translated from Russian): "well, since you singled them out, make the changes". Item 3 of that comparison (translated): "The guard against `git push --force` is text only. The rule is written in `global/AGENTS.md:120`; you put it under Gates a hook could hold yourself, but the hook is not made. Pocock's substring script would fire on `git commit -m "no --force here"`; the rule belongs in the guard on top of its own command reading."
