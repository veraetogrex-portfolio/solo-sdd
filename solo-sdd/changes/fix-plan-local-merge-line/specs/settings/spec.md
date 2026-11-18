## MODIFIED Requirements

### Requirement: Local merge method
The key `delivery.local-merge` (`merge`, `squash`, `rebase`; default `merge`) SHALL choose how `sdd-dispatch.py land-local` merges the change branch; `delivery.merge` SHALL describe only pull requests. `config describe delivery.merge` SHALL name `delivery.local-merge` for local delivery.

#### Scenario: The default keeps today
- **WHEN** the file has no `delivery.local-merge`
- **THEN** `config get delivery.local-merge` prints `merge` with `source: default`

#### Scenario: The plan line in local mode
- **WHEN** `delivery.mode` is `local`, `delivery.merge` is `rebase` and `delivery.local-merge` is not set
- **THEN** the third line of `sdd-dispatch-plan.py` is `delivery: local (<source>), local merge: merge (default)`, and it names no PR merge method

#### Scenario: The plan line in pr mode
- **WHEN** `delivery.mode` is `pr` and `delivery.merge` is `squash` from `AGENTS.md`
- **THEN** the third line stays `delivery: pr (AGENTS.md), merge: squash (AGENTS.md)`
