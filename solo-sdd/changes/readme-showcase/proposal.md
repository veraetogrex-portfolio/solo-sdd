# Proposal

## Why

On 2026-11-14 `README.md` was 59.5 KB and 9 276 words, four times the longest README of the five comparable spec-driven tools read that day (6.6-14.8 KB, median 11.0 KB). 51.2 KB of it (86%) is reference: the command table, settings, integrations, hooks, the full stop table, the agent table and the developer sections. A first reader does not see how a change looks, which skills exist (`blockers`, `context-resume`, `evidence-research` and `work-status` are not named at all), how to update or remove solo-sdd, or the license; the quick start installs without `--hooks`, so the "hooks enforce the rules" feature is off after it and nothing says so.

## What Changes

- `README.md` becomes a showcase of at most 12 000 bytes: one-sentence intro with PyPI, npm and license badges, Quick start (with `--hooks`), "One change, start to finish" (the folder of a change and a sample requirement), Why, Skills (every shipped skill by group), Requirements, Installation, Supported agents (short), How it stops (main conditions), Update and uninstall, Docs, Contributing, License.
- The reference moves into `docs/` with its text kept: `docs/cli.md` (commands and the `solo-sdd/` tree), `docs/first-project.md` (first project and rules), `docs/settings.md` (settings and checklists), `docs/integrations.md`, `docs/hooks.md` (workflow hooks and process protection), `docs/stop-conditions.md`, `docs/agents.md`, `docs/migrate.md` (moving from an `openspec/` tree), `docs/development.md` (updating the deployment from a clone, checks, releases, what is not here). `CONTRIBUTING.md` names issues, pull requests and the checks.
- The tests that read a README section (the settings table, the agents table, the stop table, the checklist example, the described scripts, the known bypasses) read the docs file that now holds it; `tests/affected.json` maps the new files to them.
- README names OpenSpec nowhere; `docs/migrate.md` holds the move.

## Capabilities

### New Capabilities

### Modified Capabilities
- `readme-content`: Stop conditions in the README and Own features first change; Short README and Skills listed are added.
- `public-tree`: Only installable code reads the docs files too.
- `secret-guard`: Known bypasses of the Bash guard are named in `docs/hooks.md`.
- `work-hooks-subagents`: Policy file is the user's and Known bypasses of the merge guard point to `docs/hooks.md`.
- `cli`: Process guard connected names `docs/hooks.md`.

## Impact

- `README.md`, `CONTRIBUTING.md`
- `docs/cli.md`, `docs/first-project.md`, `docs/settings.md`, `docs/integrations.md`, `docs/hooks.md`, `docs/stop-conditions.md`, `docs/agents.md`, `docs/migrate.md`, `docs/development.md`
- `tests/test_readme.py`, `tests/test_settings.py`, `tests/test_providers.py`, `tests/test_public_tree.py`, `tests/test_work_hooks.py`, `tests/test_process_guard.py`, `tests/affected.json`
- `solo_sdd/providers.py`, `global/work_hooks.py` (comments that name README as the place of a table or of the known bypasses)

## Out of Scope

- Rewording the moved reference text: it moves as it is, with only its links fixed.
- A tests badge: GitHub Actions starts no jobs since 2026-11-08, a badge would show no status.
- Extending the citation and clone-path checks of `tests/test_public_tree.py` to `docs/`.
- A documentation site.

## Depends On

none

## Source

"Надо короче наш ридми переписать по примеру конкурентов" (2026-11-14), with the comparison report "README solo-sdd против README конкурентов (14.11.2026)".
