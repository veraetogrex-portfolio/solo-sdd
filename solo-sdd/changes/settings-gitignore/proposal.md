# Proposal

## Why

What a project keeps out of git is decided in prose: `project-init` step 2 tells the agent to add `.env`, keys and working data, then appends only `.claude/worktrees/` by a shell line (`skills/project-init/SKILL.md:15`); `solo-sdd init` writes no `.gitignore` at all. Whether the change archive or `docs/waiting.md` are published is a manual `.gitignore` edit (this repository's own `.gitignore`). The owner has no setting to see or change this list, and no command to apply it.

## What Changes

- A key `git.ignore` (paths, default `.claude/worktrees/, .env, .env.*, !.env.example`) in a new group `git`; an item starting with `!` re-includes a path, so the `.env.example` that `project-init` writes stays in git. A value whose item hides `solo-sdd/` (the archive aside), `AGENTS.md` or `CLAUDE.md` by git's matching, or starts with `#`, is refused.
- A command `solo-sdd ignore [--write]`: without `--write` it prints the lines it would add; with it, it rewrites only the block between `# solo-sdd:begin` and `# solo-sdd:end` of `.gitignore` (creating the file or the block), with each listed path that no rule of the repository's `.gitignore` files outside the block already hides (the owner's `.git/info/exclude` and global excludes do not count: they do not travel with the repository); the rest of the file keeps its bytes. An empty list removes the block; a broken block or a folder outside git is refused with every file unchanged.
- A listed path git already tracks is not removed from git: the command names it and the `git rm --cached` line for the owner.
- `solo-sdd init` and `project-init` run it after the process tree exists; `config set` / `unset git.ignore` and the settings screen print the hint to run it.

## Capabilities

### New Capabilities


### Modified Capabilities
- `settings`: Ignore list setting, Process paths stay tracked, Ignore command and Ignore command refusals are added.
- `project-init`: Built-in worktree folder ignored, Process artifacts in git and Hidden process artifacts are modified (the solo-sdd block from `git.ignore` through `solo-sdd ignore --write` replaces the single appended line).

## Impact

- `solo_sdd/settings.py`, `global/sdd_pr.py`, `global/sdd_dispatch_plan.py`, `global/sdd_worktree.py`, `global/work_hooks.py`, `docs/settings.md`, `tests/test_settings.py`, `tests/stands/settings-tui.py`, `solo_sdd/cli.py`, `solo_sdd/init.py`, `solo_sdd/settings_ui.py`, `skills/project-init/SKILL.md`, `docs/cli.md`, `tests/test_cli.py`, `tests/test_init.py`, `tests/test_skill_commands.py`, `tests/stands/settings-gitignore.py`

## Out of Scope

- Untracking files already in git: left to the owner by the printed command.
- Hiding `solo-sdd/`, `AGENTS.md` or `CLAUDE.md`: refused, Process artifacts in git keeps them tracked.
- The other units of the same plan: `settings-delivery-items`, `settings-ci-wait`, `settings-local-merge`, `settings-branch-names`, `settings-agent-models`, `settings-change-limits`, `settings-working-copy`, `settings-stop-hooks`, `settings-project-rules`.

## Depends On

none

## Source

The owner, 2026-11-17 (translated from Russian): "I see we made a CLI, but I do not see the settings of our project inside; I want to edit everything that can be edited: how we work with PRs, how we work with subagents, how we work with the project, what we put into gitignore, and so on. A super precise configuration is needed."
