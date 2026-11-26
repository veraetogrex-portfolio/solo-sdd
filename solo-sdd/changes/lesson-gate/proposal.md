# Proposal

## Why

Section 15 of the global rules turns every lesson into a line of the project's `## Lessons`, at most 20 lines (`lessons.max-lines`), loaded into every session of that project. Some of those lessons are mechanical: a fixed text pattern, a banned command or character, an import form, a file location. A check catches such a cause every time; a line in `AGENTS.md` only asks the next agent to remember it. solo-sdd already moves its own mechanical gates out of text where it can: `docs/skills-audit.md` marks each text gate `hook: yes` or `hook: no` and lists the first under "Gates a hook could hold". The lessons of a consumer project get no such sorting, so a mechanical cause stays a line forever and takes a slot of the 20.

The `retro` skill of Matt Pocock (https://github.com/mattpocock/skills, `skills/engineering/retro/SKILL.md`) draws the line this change takes: a mechanical violation gets a deterministic check (a lint rule, a pre-commit hook, a CI job), and the written standards keep only judgement calls.

## What Changes

- Section 15 of `global/AGENTS.md`: when a lesson's class of cause is mechanical, the agent writes the lesson as now and also gives the report line `Lesson gate: <the check> — <where it would run>`; a judgement-call lesson gets no such line. The line starts with `Lesson`, so the status block of an orchestrator and the dispatcher's `Lessons:` line carry it with no change to `spec-dispatch`.
- When a change adds a check that refuses every case a lesson's words name, the same change removes that line from `## Lessons` and keeps its text under its id in `LESSONS.md` with `Held by: <check>`; a check that refuses only some keeps the line. The search for duplicates reads the `Held by:` entries too, so the same correction later writes no second line.
- The report form of `spec-next` names `Lesson gate:` among its extra lesson lines.

## Capabilities

### New Capabilities

### Modified Capabilities
- `lesson-routing`: ADDED requirements Gate for a mechanical lesson and Lesson held by a check.

## Impact

- `global/AGENTS.md`
- `skills/spec-next/SKILL.md`
- `tests/test_skill_commands.py`

## Out of Scope

- Building the check itself: the line proposes it, the owner plans it.
- Lessons about the solo-sdd process (`Lesson for solo-sdd:`): they keep going to the report only.
- The text of `skills/spec-dispatch/`: lines starting with `Lesson` already reach its report.
- Neighbouring changes of this plan: `codex-user-only-skills`, `guard-fails-closed`, `history-guard`.

## Depends On

none

## Source

The owner, 2026-11-26, on the comparison of solo-sdd with mattpocock/skills, skyremote/chief-of-staff-kit and davidondrej/skills (translated from Russian): "well, since you singled them out, make the changes". Item 4 of that comparison (translated): "Mechanical lessons into a check, not into AGENTS.md. Now `lesson-routing` writes any lesson as a line of `## Lessons`. Pocock's `retro` separates them strictly: a mechanical violation is closed by a linter, a hook or a check in `solo-sdd validate`; only judgement calls stay as rule text."
