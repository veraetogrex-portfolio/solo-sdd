# integration-skills Specification

## Purpose
Lays out the skills an owner integration ships into the agents' skill folders by the same rules as the solo-sdd skills, shows them in the status and removes them when the integration is gone, so a third-party skill never has to be added to the core.

## Requirements

### Requirement: Integration skills laid out
`solo-sdd install` and `solo-sdd update` SHALL lay out every `skills/<skill>/SKILL.md` of each readable owner integration into the skill root of every chosen agent, with the drift, backup and foreign-copy rules of the solo-sdd skills. An owner integration with a broken description SHALL have no skill laid out and, when it has a `skills` folder, SHALL be named in the output.

#### Scenario: A skill reaches every agent
- **WHEN** the owner folder holds `dup-scan/skills/dup-scan-review/SKILL.md` and the chosen agents are `claude, codex`
- **THEN** after `solo-sdd update` the skill is in the skill root of both agents

#### Scenario: A copy edited in place
- **WHEN** the laid-out copy was edited in place and `update` runs
- **THEN** the copy is kept and shown as `drift`, as for a solo-sdd skill

### Requirement: Integration skill status rows
`solo-sdd status` SHALL show every laid-out integration skill copy on its own row whose name is `integration:<name>`, with the same states as the other rows.

#### Scenario: A status row
- **WHEN** the skill of `dup-scan` is laid out and unchanged
- **THEN** `solo-sdd status` has an `ok` row named `integration:dup-scan` with the copy path

### Requirement: Skill name taken
A skill whose name is taken by a solo-sdd skill or by a skill of an integration earlier in name order, whose folder name breaks the `<name>` rule, whose folder or `SKILL.md` is a link, or whose `SKILL.md` is missing, not a regular file, over 1 MB or not UTF-8, SHALL NOT be laid out; `install` and `update` SHALL name it with the reason (and the owner of a taken name), and the other copies SHALL still be laid out.

#### Scenario: A name of a solo-sdd skill
- **WHEN** an owner integration ships `skills/ship/SKILL.md`
- **THEN** `update` names `ship` as taken by solo-sdd, keeps the solo-sdd `ship` copy and lays out the other skills

#### Scenario: A linked skill file
- **WHEN** `skills/dup-scan-review/SKILL.md` is a link to a file outside the integration folder
- **THEN** `update` names it as a link and lays out no copy of it

### Requirement: Integration skills removed with their source
When an owner integration folder or one of its skills is gone or refused, the next `update` SHALL remove only the copies the layout state records from it that the current layout does not lay out, name each removed path, and keep a copy edited in place as `drift`; a source it lacks the permission to read SHALL keep its copies and be named.

#### Scenario: Integration folder deleted
- **WHEN** the `dup-scan` folder is deleted and `update` runs
- **THEN** its skill copies are removed and named, and no other copy changes

#### Scenario: A closed source
- **WHEN** the `dup-scan/skills` folder cannot be listed or entered and `update` runs
- **THEN** its copies stay, their names stay taken from integrations later in name order, and the read error is named
