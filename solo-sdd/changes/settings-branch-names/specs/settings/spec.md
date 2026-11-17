## ADDED Requirements

### Requirement: Branch and commit prefixes
The change branch SHALL be `<delivery.branch-prefix><id>` (default `change/`), the plan branch `<delivery.plan-prefix><first id>` (default `plan/`), and a light commit subject SHALL start with `commit.light-prefix` (text, default `light:`), matched as plain text. The dispatch scripts, `sdd-pr.py`, `sdd-eval.py`, `spec-dispatch`, `spec-plan`, `work-status`, `report` and the global rules SHALL take them; `change/<id>`, `plan/<first id>` and `light:` in other requirements name these defaults.

#### Scenario: A team prefix
- **WHEN** the file has `delivery.branch-prefix: feat/`, open changes `a` and `b` are ready, and the repository has branches `change/a` and `feat/b`
- **THEN** `sdd-dispatch-plan.py` prints `launch: a`, and `b` waits with `not merged: branch feat/b`

#### Scenario: Defaults keep the names
- **WHEN** the file has none of the three keys, and the repository has branch `change/a`
- **THEN** `a` waits with `not merged: branch change/a`, and `work-status` counts commits whose subject starts with `light:`

#### Scenario: A light prefix with pattern characters
- **WHEN** the file has `commit.light-prefix: [quick]`, and the log has `[quick] fix typo` and `q fix`
- **THEN** `work-status` counts one light commit

### Requirement: Prefix change guard
`config set` and `config unset` of `delivery.branch-prefix`, and the settings screen, SHALL refuse a value other than the one in effect, while a local branch `<prefix in effect><id>` of an open change exists, with exit 1, the branch names and the file unchanged. A prefix for which `<prefix>a` is not a valid git branch name, and equal branch and plan prefixes, SHALL be refused. Outside a git repository the branch check passes; a failed branch listing SHALL refuse with git's message.

#### Scenario: A leftover change branch
- **WHEN** the repository has branch `change/a`, `a` is an open change, and `config set delivery.branch-prefix feat/` runs
- **THEN** exit 1 names `change/a`, `config get delivery.branch-prefix` still prints `change/`

#### Scenario: A branch of an archived change
- **WHEN** the repository has branch `change/old`, `old` is archived, and `config set delivery.branch-prefix feat/` runs
- **THEN** code 0, `config get delivery.branch-prefix` prints `feat/`

#### Scenario: Equal prefixes
- **WHEN** `config set delivery.plan-prefix change/` runs while `delivery.branch-prefix` is `change/`
- **THEN** exit 1 names `delivery.branch-prefix`, the file is unchanged

#### Scenario: A prefix git refuses
- **WHEN** `config set delivery.branch-prefix "feat/*"` runs
- **THEN** exit 1 names a valid branch name, the file is unchanged
