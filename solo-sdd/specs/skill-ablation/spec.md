# skill-ablation Specification

## Purpose
What each skill gives the current main model is measured by running the same tasks with the full skill, without its method steps and without the skill, and the measurement is repeated when the main model changes.

## Requirements

### Requirement: Skills audit table
`docs/skills-audit.md` SHALL hold a section per skill of `targets.json` with a row per step marked `gate (code)`, `gate (text)` or `method`; a step is a top-level `N.`, `Na.` or `**N.` item of `SKILL.md` outside fenced code, up to the next item or heading, with its step files, keyed by heading, number and title; a skill without items has one `whole text` row. A test SHALL read the step tables only and fail on a missing section, a step without a row, a row without a step, or another mark.

#### Scenario: A new skill without a section
- **WHEN** a skill is added to `targets.json` and `docs/skills-audit.md` has no section for it
- **THEN** the audit table test fails naming the skill

#### Scenario: A step without a row
- **WHEN** a skill gets a new step `9.` and its section has no row for it
- **THEN** the audit table test fails naming the skill and the step

#### Scenario: A skill without steps
- **WHEN** a skill's `SKILL.md` has no top-level numbered item and its section has one `whole text` row
- **THEN** the audit table test passes for that skill

### Requirement: Gates a hook could hold
Every `gate (text)` row SHALL carry `hook: yes` or `hook: no`, and `docs/skills-audit.md` SHALL end with a section `Gates a hook could hold` listing the `hook: yes` rows, for the owner to plan as changes. The audit table test SHALL fail on a `gate (text)` row without either value and on a `hook: yes` row missing from that section.

#### Scenario: A text gate a hook could hold
- **WHEN** a `gate (text)` row is marked `hook: yes`
- **THEN** it is listed in `Gates a hook could hold`, and the audit table test fails if it is missing there

#### Scenario: A text gate without a hook value
- **WHEN** a `gate (text)` row has an empty hook column
- **THEN** the audit table test fails naming the skill and the step

### Requirement: Ablation runner
`tests/stands/skill-ablation.py prepare <skill> --budget <calls>` SHALL create a new run folder (`--out <dir>`, refused when not empty; else a fresh temporary one), print its path, copy each task's files, write a manifest and one prompt per variant, task by task (full skill, without its `method` steps, no skill), at most the budget, each run by a Claude Code subagent of the lead session under the description it names, never by `claude -p`. A skill with no `method` step gets no cut variant.

#### Scenario: The budget is reached
- **WHEN** the set has 2 tasks, and `prepare --budget 4` is given
- **THEN** it writes 4 prompts and the line `budget reached: 2 of 6 calls not made`, exit 3

#### Scenario: A repeated prepare
- **WHEN** `prepare` runs twice for the same skill
- **THEN** each run gets its own folder and the first run's files do not change

### Requirement: Ablation grade
`grade <run>` SHALL read each prompt's transcript `<run>/<id>.jsonl` (with `--from <dir>`, first copied from the one regular `agent-*.jsonl` there whose `meta.json` description equals the prompt's), take the answer from the last `SubagentHandback` message or else the last assistant text, run the task's check script on the answer as a file, never executing it, and print one row per prompt with the outcome, the path (required tool calls found) and the tokens of the last assistant turn.

#### Scenario: A missing answer
- **WHEN** `grade` finds a prompt without a saved transcript, or a transcript without an answer
- **THEN** its row is `not run`, and the run's summary counts it apart from failures

### Requirement: Grade outcomes
A row SHALL be, first match wins: `unreadable` (a line not JSON, over 64 MB, or two `--from` matches), `not run` (no answer), `leaked`, `pass` (the check exits 0 and every required tool call is there), else `fail`. `grade` SHALL print the models and `compare: full <a> of <n>, cut <b> of <n>, none <c> of <n>` (`cut - of <n>` without a cut variant), the passes over the tasks with every variant prepared and graded `pass` or `fail`, and count other outcomes and calls not made apart.

#### Scenario: A broken transcript
- **WHEN** a transcript has a line that is not JSON
- **THEN** its row is `unreadable` with that line's number, and the task is left out of `compare:`

#### Scenario: A leaked row whose check passes
- **WHEN** a transcript has a `Skill` call for the skill and an answer the check passes
- **THEN** the row is `leaked`, not `pass`

### Requirement: Runner input refused
`prepare` SHALL refuse with exit 2, before writing anything, a skill that is not a key of `skills` in `targets.json` or has no task set under `tests/stands/skill-ablation/`. `grade` SHALL read only the files its manifest names inside the run folder, and the `--from` folder, and SHALL refuse with exit 2 a manifest whose id, task or variant is not one `prepare` writes.

#### Scenario: A path as the skill name
- **WHEN** `prepare ../x --budget 6` is given
- **THEN** it exits 2 naming the skill, and no folder is created

### Requirement: Full skill out of reach in the cut variants
Every prompt SHALL carry its variant's text inline (the whole skill, the skill without its `method` steps, or none) and forbid loading the skill and reading the task sets. The variants share the lead session's context (laid-out global rules, project rules, skill listing); the ban wins over their pointers. `grade` SHALL mark a row `leaked`, out of the comparison, when its transcript has a `Skill` call for the skill or a tool input naming `skills/<skill>/` or `tests/stands/skill-ablation/`.

#### Scenario: The skill is loaded anyway
- **WHEN** the transcript of a no-skill row has a `Skill` call for `evidence-research`
- **THEN** the row is `leaked`, and the table counts it as neither a win nor a loss

#### Scenario: The answer key is read
- **WHEN** the transcript of a full row reads `tests/stands/skill-ablation/debug-profile/dp-code/reference.jsonl`
- **THEN** the row is `leaked`

#### Scenario: A laid-out copy is read
- **WHEN** the transcript of a cut row reads `~/.claude/skills/debug-profile/SKILL.md`
- **THEN** the row is `leaked`

### Requirement: Task sets
Each task folder `tests/stands/skill-ablation/<skill>/<task>/` SHALL hold `prompt.md`, `fixture/`, `check.py` (argument: the answer file; exit 0 on a pass), `required.txt` (a regular expression per line, matched against `<tool> <input JSON>` of each tool call) and `reference.jsonl` (a Claude Code transcript with the required calls and an answer). A test SHALL fail when the reference does not grade `pass` or the check passes an empty answer. `evidence-research` uses only local sources.

#### Scenario: A check that passes an empty answer
- **WHEN** a task's `check.py` exits 0 on an empty answer file
- **THEN** the task set test fails naming the task

### Requirement: Measurement on a main model change
`docs/release.md` SHALL require the runner on every skill with a task set when the `main` list of `model-policy.json` changes, its grade output going into that skill's section of `docs/skills-audit.md` under `### Run <date> <model>`. A skill whose last two runs with a compared task each have full passes no more than none passes SHALL carry `candidate to cut: the owner decides`; only the owner removes that line or the skill.

#### Scenario: Two lost runs
- **WHEN** `docs/skills-audit.md` holds two runs in a row where `evidence-research` scored no better than the no-skill variant
- **THEN** its section has the line `candidate to cut: the owner decides`, the audit table test fails without that line, and the skill stays in the repository

#### Scenario: A run without a compared task
- **WHEN** a run's `compare:` line has `of 0`
- **THEN** the run counts as neither a win nor a loss
