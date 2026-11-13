# rules-hygiene Specification

## Purpose
The rules solo-sdd deploys to agents (skills, global rules, the algorithm, templates) contain no instructions written for older models, no rituals and no contradictions.

## Requirements

### Requirement: Prompt audit without open findings
A `/claude-api prompt-audit` run over `skills/*/SKILL.md`, `global/AGENTS.md`, `ALGORITHM.md` and `templates/` SHALL give no open findings: every finding is fixed or recorded in `docs/rules-audit.md` with a reason; a finding whose edit was rolled back by an eval set run also carries that run's label.

#### Scenario: A repeated audit
- **WHEN** after the edits `prompt-audit` runs over the same files again
- **THEN** each of its findings is either absent or present in `docs/rules-audit.md` with a reason, and one rolled back by a run also with the run label

#### Scenario: An edit made the result worse
- **WHEN** the set run after removing a rule is worse than the run before by the decision rule of `dispatch-orchestrator-solo`
- **THEN** the rule is returned, and the finding is recorded in `docs/rules-audit.md` with the label of this run

### Requirement: Skill usage report
`docs/rules-audit.md` SHALL hold the number of calls and the cost of every skill from `/skill-doctor`, and without it the number of calls from the local session history with the period and a note that the cost is not measured. Skills without calls go to the owner as a list; only the owner deletes them.

#### Scenario: A skill without calls
- **WHEN** a skill has no calls in the report period
- **THEN** the skill stays in the repository and is in the "Needs from you" section of `docs/rules-audit.md`
