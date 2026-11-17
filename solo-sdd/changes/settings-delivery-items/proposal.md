# Proposal

## Why

Three items of the AGENTS.md section "Delivery" are prose that only agents read: "PR title:", "Deploy:" and "Owner only:" (`skills/project-init/SKILL.md:70`, `global/sdd_pr.py:42`). They are not in the settings registry (`solo_sdd/settings.py` REGISTRY), so `solo-sdd config` and `solo-sdd settings` cannot show or change them, and the owner edits AGENTS.md by hand. The registry has no kind for free text, which the PR title rule and the deploy note need. A PR can also change `solo-sdd/config` itself and weaken a gate (`delivery.merge-by`, the owner paths) with no owner look.

## What Changes

- A new settings kind `text`: one line of printable characters, at most 200, no line break; `describe` names it, the settings screen edits it as a one-line input.
- Keys `delivery.pr-title` (text, default `the change name`), `delivery.deploy` (text, default `no`) and `delivery.owner-only` (paths, default empty); without a file value each takes its "Delivery" item of `AGENTS.md`, source `AGENTS.md`, as `delivery.mode` does.
- The owner gate of `sdd-pr.py merge`/`land` and `sdd-dispatch.py land-local` takes the paths of `delivery.owner-only` from the main folder plus `.github/workflows/**`, an edit of `solo-sdd/config` in the change waits for the owner (code 8), and broken settings stop the merge (code 1) instead of opening the gate.
- `ship`, `spec-dispatch` and `project-init` read the three values through `solo-sdd config get`.

## Capabilities

### New Capabilities


### Modified Capabilities
- `settings`: Text settings and Delivery items in config are added; Defaults by mode is modified (a key's old source named by its requirement).
- `pr-tool`: Owner-only paths gate is modified (the paths from the main folder's setting, an edit of `solo-sdd/config` waits for the owner, broken settings give code 1).

## Impact

- `solo_sdd/settings.py`, `global/sdd_pr.py`, `global/sdd_dispatch_plan.py`, `global/sdd_worktree.py`, `global/work_hooks.py`, `docs/settings.md`, `tests/test_settings.py`, `tests/stands/settings-tui.py`, `global/sdd_dispatch.py`, `solo_sdd/settings_ui.py`, `skills/ship/SKILL.md`, `skills/spec-dispatch/preparation.md`, `skills/spec-dispatch/merge.md`, `skills/project-init/SKILL.md`, `tests/test_sdd_pr.py`, `tests/test_sdd_dispatch.py`, `tests/test_settings_ui.py`, `tests/test_skill_commands.py`, `tests/stands/settings-delivery-items.py`

## Out of Scope

- CI wait, merge gates and PR shape keys: `settings-ci-wait`.
- Branch and commit prefixes: `settings-branch-names`.
- The "Working copy" items: `settings-working-copy`.
- Removing the "Delivery" items from `AGENTS.md`: they stay the old source.
- The other units of the same plan: `settings-ci-wait`, `settings-local-merge`, `settings-branch-names`, `settings-agent-models`, `settings-change-limits`, `settings-gitignore`, `settings-working-copy`, `settings-stop-hooks`, `settings-project-rules`.

## Depends On

none

## Source

The owner, 2026-11-17 (translated from Russian): "I see we made a CLI, but I do not see the settings of our project inside; I want to edit everything that can be edited: how we work with PRs, how we work with subagents, how we work with the project, what we put into gitignore, and so on. A super precise configuration is needed."
