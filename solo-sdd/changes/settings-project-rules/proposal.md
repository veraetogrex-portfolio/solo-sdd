# Proposal

## Why

Three project rules are read from prose or from the global rules for every project alike: the project stage `demo`/`prod` (the `Mode:` line of `solo-sdd/project.md`, `global/AGENTS.md:101-103`), the language of the change artifacts (the `Language:` line, `templates/solo-sdd/project.md:3`, read by no command) and the `## Lessons` routine (a lesson written into `AGENTS.md` without asking, at most 20 lines, `global/AGENTS.md:130-134`). The owner cannot see or change them with `solo-sdd config`, and a project where lessons must not be written has no switch.

## What Changes

- Keys `project.stage` (`demo`, `prod`; empty by default: decided by the task), `artifacts.language` (2 or 3 lowercase letters, `en`), `lessons.write` (`on`, `off`; `on`) and `lessons.max-lines` (int, 20), in group `process`; an agent changes them only on the owner's words.
- Without a file value `project.stage` and `artifacts.language` take the `Mode:` and `Language:` lines of `solo-sdd/project.md`, source `project.md`; neither line is removed, a file value wins over the line, and a line value outside the allowed ones is named on stderr.
- The global rules, `project-init` and `spec-plan` read them through `solo-sdd config get`; `lessons.write: off` makes a lesson go into the report as `Lesson (not written): <sentence>`.

## Capabilities

### New Capabilities


### Modified Capabilities
- `settings`: Project rules in config and Project lines as the old source are added; Config command names the source `project.md`.
- `lesson-routing`: Lesson from a correction or a fix takes `lessons.write: off`.

## Impact

- `solo_sdd/settings.py`, `global/sdd_pr.py`, `global/sdd_dispatch_plan.py`, `global/sdd_worktree.py`, `global/work_hooks.py`, `docs/settings.md`, `tests/test_settings.py`, `tests/stands/settings-tui.py`, `global/AGENTS.md`, `ALGORITHM.md`, `skills/project-init/SKILL.md`, `skills/spec-plan/SKILL.md`, `templates/solo-sdd/project.md`, `tests/test_skill_commands.py`, `tests/stands/settings-project-rules.py`

## Out of Scope

- Moving the intent text of `project.md` into the config: it is prose, not a setting.
- The working copy items: `settings-working-copy`.
- The other units of the same plan: `settings-delivery-items`, `settings-ci-wait`, `settings-local-merge`, `settings-branch-names`, `settings-agent-models`, `settings-change-limits`, `settings-gitignore`, `settings-working-copy`, `settings-stop-hooks`.

## Depends On

settings-delivery-items

## Source

The owner, 2026-11-17 (translated from Russian): "I see we made a CLI, but I do not see the settings of our project inside; I want to edit everything that can be edited: how we work with PRs, how we work with subagents, how we work with the project, what we put into gitignore, and so on. A super precise configuration is needed."
