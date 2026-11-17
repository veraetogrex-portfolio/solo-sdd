## ADDED Requirements

### Requirement: Local merge method
The key `delivery.local-merge` (`merge`, `squash`, `rebase`; default `merge`) SHALL choose how `sdd-dispatch.py land-local` merges the change branch; `delivery.merge` SHALL describe only pull requests. `config describe delivery.merge` SHALL name `delivery.local-merge` for local delivery.

#### Scenario: The default keeps today
- **WHEN** the file has no `delivery.local-merge`
- **THEN** `config get delivery.local-merge` prints `merge` with `source: default`
