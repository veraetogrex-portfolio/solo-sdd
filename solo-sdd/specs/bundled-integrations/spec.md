# bundled-integrations Specification

## Purpose
Ships the pinned outside copies of solo-sdd as integrations bundled with the package: a third source below the project and the owner ones, enabled by default, switched off per project through the same CLI as any other integration.

## Requirements

### Requirement: Bundled source
The package SHALL ship `integrations/<name>/` folders of the repository as a third source, read from the installed package or the clone. A project or owner integration with the same name SHALL shadow the bundled one, and `integrations list` SHALL show the source `bundled`.

#### Scenario: Bundled integrations listed
- **WHEN** `solo-sdd integrations list` runs in a project with no settings
- **THEN** it prints `antislop bundled enabled review` and `security-audit bundled enabled audit`

#### Scenario: A project folder shadows a bundled one
- **WHEN** the project holds `solo-sdd/integrations/antislop/` and `integrations list` runs
- **THEN** it prints `antislop project disabled` and a line naming the bundled copy as shadowed

### Requirement: Bundled default state
A bundled integration SHALL be enabled unless the `integrations.off` setting (a list of names, empty by default) names it. `integrations disable <name>` of a bundled integration SHALL add it to `integrations.off`, and `enable <name>` SHALL remove it, each changing only that line. `integrations.off` SHALL act only on a name whose used folder is bundled, and a bundled name written into `integrations` SHALL NOT change its state.

#### Scenario: Switched off in one project
- **WHEN** `solo-sdd integrations disable antislop` runs
- **THEN** `solo-sdd config get integrations.off` prints `antislop` and `integrations list` shows `antislop bundled disabled`

### Requirement: Material by tag
An integration MAY have `tags`, a list of names. `solo-sdd check --point review|audit --tag <tag>` SHALL list only the material of enabled integrations of that point with that tag, outside a project the bundled ones, and with none a line starting `no integrations enabled`. A call without `--tag` SHALL list only names of `integrations`, as before.

#### Scenario: The interface material
- **WHEN** `check --point review --tag ui` runs in a project with defaults
- **THEN** it prints `MATERIAL antislop:` with the path of its core rules file and nothing for `security-audit`

#### Scenario: Outside a project
- **WHEN** `check --point audit --tag security` runs in a folder without `solo-sdd/`
- **THEN** it prints `MATERIAL security-audit:` and exits 0

#### Scenario: An untagged call
- **WHEN** `integrations` is empty and `check --point review` runs in a project with defaults
- **THEN** it prints `no integrations enabled` and exits 0

### Requirement: Skills read rules by point and tag
`ui-check`, `copy-check` and `spec-next` step 7a SHALL take their rules from `check --point review --tag ui` (`--tag copy` for `copy-check`), `spec-audit` from `check --point audit --tag security`; when it lists nothing, the skill SHALL say in its report that those rules are off in the project and SHALL NOT read the laid-out copy. While a bundled integration is disabled, the requirements that read its rules SHALL NOT apply in that project.

#### Scenario: Rules off
- **WHEN** `antislop` is disabled in a project and `ui-check` runs there
- **THEN** the skill text makes the report say the interface rules are off in this project
