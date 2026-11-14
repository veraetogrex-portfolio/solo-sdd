## ADDED Requirements

### Requirement: Merge only on green CI
`AGENTS.md` and `docs/release.md` SHALL say that an agent merges a PR only when `sdd-pr.py wait` gives `CI: green`, and that on `CI: red` or `CI: infra` the PR waits for the owner; they SHALL NOT tell an agent to merge around a red or missing check, and SHALL NOT say that Actions starts no jobs.

#### Scenario: A PR with green checks
- **WHEN** an agent delivers a change in `pr` mode and `wait` gives `CI: green`
- **THEN** both files let the agent merge it through `sdd-pr.py merge`, where `delivery.merge-by` lets an agent merge

#### Scenario: A PR whose checks are red or did not start
- **WHEN** `wait` gives `CI: red` or `CI: infra`
- **THEN** both files say the PR waits for the owner and that an agent never merges around a red or missing check

## REMOVED Requirements

### Requirement: Delivery without CI
