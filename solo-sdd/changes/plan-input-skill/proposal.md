# Proposal

## Why

An input for `/spec-plan` and a task text for another agent were built from scratch six times in two weeks: 10.11 (…b37fd2), 12.11 (…52f217), 15.11, 16.11 (…cd16b2, "make a TZ for the video for Claude"), 17.11 (…ebbc13, "well, write the TZ") and 20.11 (…8ec6ec). On 15.11 `/spec-dispatch`, `/spec-plan` and `/project-init` were started in the notes folder, where no `solo-sdd/` tree exists, and did nothing. On 23.11 the owner got a personal copy of a skill `plan-input` in `~/.codex/skills/plan-input/SKILL.md` (4,671 bytes), outside this repository: it is not in git, not deployed to Claude Code, and `sync.py push` keeps it as a foreign copy.

## What Changes

- A skill `plan-input` in `skills/plan-input/SKILL.md`, the text of the personal copy with its Cyrillic trigger phrases replaced by English ones (the repository test rejects Cyrillic): it writes one self-contained Markdown input for `/spec-plan` per target repository from the owner's quoted decisions, checks every item against the repository (done by a commit, planned by an open change, a missing file or line under `Not checked`, each item under one section), says that only its letter sections are planned and counts the other sections in the reply, saves it next to its source, in a named folder or in `~/Documents/plan-input/` but never inside the target repository and never over an earlier input, gives the three launch lines (folder, command, `/spec-dispatch`), and writes nothing for a target without git or a `solo-sdd/` tree or when nothing is left to plan.
- `targets.json` (and its copy of the previous map, `tests/targets-before.json`) deploys it to Claude Code, Codex and the other agents; it is listed with the manual commands in section 14 of `global/AGENTS.md`, the README table and `docs/layout.md`, and gets its section in `docs/skills-audit.md`.
- A stand `tests/stands/plan-input.py` grades an input the skill writes from a fixture review.

## Capabilities

### New Capabilities
- `plan-input`: a self-contained input for `/spec-plan` from the owner's decisions, checked against the target repository, with the launch steps.

### Modified Capabilities

## Impact

- `skills/plan-input/SKILL.md`
- `targets.json`
- `tests/targets-before.json`
- `global/AGENTS.md`
- `README.md`
- `docs/layout.md`
- `docs/skills-audit.md`
- `tests/stands/plan-input.py`
- `tests/stands/plan-input/`

## Out of Scope

- The personal copy `~/.codex/skills/plan-input/SKILL.md`: the delivery's layout replaces it (`sync.py push --replace-foreign`, with a backup); the owner's Claude Code plugin skill `plan-input:plan-input`, if it stays installed, is the owner's to remove.
- Writing the input into the target repository or starting `/spec-plan` from the skill: the skill hands the launch to the owner.
- Neighbouring changes of this plan: `action-first-project-repo`, `worktree-add-quiet`, `fix-env-dump-text-words`.

## Depends On

none

## Source

The owner, 2026-11-23, on the decisions of the weekly review of 16-22.11 (translated from Russian): "all except the proxy, yes", then "do it". Item E of the owner's input file "2026-11-23 input for spec-plan" (name translated): "the skill plan-input in solo-sdd".
