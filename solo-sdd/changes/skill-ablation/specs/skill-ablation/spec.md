## Purpose

What each skill gives the current main model is measured by running the same tasks with the full skill, without its method steps and without the skill, and the measurement is repeated when the main model changes.

## ADDED Requirements

### Requirement: Skills audit table
`docs/skills-audit.md` SHALL hold every skill of `targets.json` with a row per step marked `gate (code)`, `gate (text)` or `method`. A step SHALL be a top-level `N.`, `Na.` or `**N.` item of `SKILL.md` with its step file; a skill without such items SHALL have one row for its whole text. A test SHALL fail on a skill without a section, a step without a row, or another mark.

#### Scenario: A new skill without a section
- **WHEN** a skill is added to `targets.json` and `docs/skills-audit.md` has no section for it
- **THEN** the audit table test fails naming the skill

#### Scenario: A step without a row
- **WHEN** a skill gets a new step `9.` and its section has no row for it
- **THEN** the audit table test fails naming the skill and the step

### Requirement: Gates a hook could hold
Every `gate (text)` row SHALL carry `hook: yes` or `hook: no`, and `docs/skills-audit.md` SHALL end with a section `Gates a hook could hold` listing the `hook: yes` rows, for the owner to plan as changes.

#### Scenario: A text gate a hook could hold
- **WHEN** a `gate (text)` row is marked `hook: yes`
- **THEN** it is listed in `Gates a hook could hold`, and the audit table test fails if it is missing there

### Requirement: Ablation runner
`tests/stands/skill-ablation.py prepare <skill> --budget <calls>` SHALL write one prompt per variant and task (full skill; without its `method` steps; no skill, only `global/AGENTS.md`), at most the budget, each to be run by a Claude Code subagent of the lead session, never by `claude -p`. `grade <run>` SHALL check each saved answer by the task's script and the required commands in that subagent's transcript, and print one row per variant and task with the outcome, the path and the tokens.

#### Scenario: The budget is reached
- **WHEN** the set has 2 tasks, and `prepare --budget 4` is given
- **THEN** it writes 4 prompts and the line `budget reached: 2 of 6 calls not made`, exit 3

#### Scenario: A missing answer
- **WHEN** `grade` finds a prompt without a saved answer or transcript
- **THEN** its row is `not run`, and the run's summary counts it apart from failures

### Requirement: Full skill out of reach in the cut variants
The prompt of the variant without `method` steps and of the no-skill variant SHALL carry its own text and forbid loading the skill. `grade` SHALL mark a row `leaked`, and leave it out of the comparison, when its transcript has a `Skill` call for that skill or a read of the skill's laid-out files.

#### Scenario: The skill is loaded anyway
- **WHEN** the transcript of a no-skill row has a `Skill` call for `evidence-research`
- **THEN** the row is `leaked`, and the table counts it as neither a win nor a loss

### Requirement: Measurement on a main model change
`docs/release.md` SHALL require the runner on the method skills when the `main` list of `model-policy.json` changes, with the result written into `docs/skills-audit.md`. A skill that did not beat the no-skill variant on two runs in a row SHALL be listed there as a candidate to cut; only the owner deletes it.

#### Scenario: Two lost runs
- **WHEN** `docs/skills-audit.md` holds two runs in a row where `evidence-research` scored no better than the no-skill variant
- **THEN** its section has the line `candidate to cut: the owner decides`, the audit table test fails without that line, and the skill stays in the repository
