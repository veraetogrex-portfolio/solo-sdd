## MODIFIED Requirements

### Requirement: Owner-only paths gate
Before the merge request `sdd-pr.py merge` and `land` SHALL check the PR files, old names of renamed ones too, against `.github/workflows/**` and the `delivery.owner-only` patterns of the main folder, never of the PR or WORKTREE (`*` within a name, `**` across folders). A match, an edit of the "Owner only:" item or of `solo-sdd/config` gives code 8 "waits for the owner: <paths>", no merge request, the PR open. Broken settings give code 1; unreadable `AGENTS.md` drops only its item.

#### Scenario: A CI edit
- **WHEN** a green PR changes `.github/workflows/ci.yml`
- **THEN** code 8 with this path, the PR is open, no merge is requested

#### Scenario: An owner path
- **WHEN** "Delivery" has "Owner only: `global/work_hooks.py`", and the PR changes this file
- **THEN** code 8 with `global/work_hooks.py`

#### Scenario: A change shortens the list
- **WHEN** the PR removes a path from the item "Owner only:" in `AGENTS.md`
- **THEN** code 8: the item is checked by the main folder's `AGENTS.md`, and an edit of the item itself waits for the owner

#### Scenario: land and AGENTS.md outside git
- **WHEN** `AGENTS.md` is ignored by git, and in the WORKTREE `AGENTS.md` the item "Owner only:" differs from the main folder
- **THEN** `land` returns code 8: the transfer after merge would bring this item into the main folder

#### Scenario: The file list failed
- **WHEN** the PR files request failed or returned something other than JSON
- **THEN** code 1, no merge is requested, the PR is open

#### Scenario: Owner paths from the config
- **WHEN** the main folder's `solo-sdd/config` has `delivery.owner-only: deploy/**`, and a green PR changes `deploy/prod.yml`
- **THEN** code 8 with `deploy/prod.yml`

#### Scenario: A PR edits the config
- **WHEN** a green PR changes the line `delivery.merge-by: human` of `solo-sdd/config` to `agent`
- **THEN** code 8 with `solo-sdd/config`, no merge is requested, also when a checklist covering it is ticked and approved by another account

#### Scenario: The config outside git
- **WHEN** `solo-sdd/config` is ignored by git, and the WORKTREE copy differs from the main folder's
- **THEN** `land` returns code 8 with `solo-sdd/config`: the transfer after merge would bring the copy into the main folder

#### Scenario: Broken settings
- **WHEN** line 2 of the main folder's `solo-sdd/config` is not `key: value`, and a green PR changes `deploy/prod.yml`
- **THEN** code 1 naming `solo-sdd/config:2`, no merge is requested, the PR is open: the gate never falls back to fewer paths
