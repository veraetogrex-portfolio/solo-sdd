=== docs/waiting.md
# Waiting

What cannot be closed without an external condition. Only the first table waits: when the condition is met, the row moves to the table under `## Closed`, right after this table, with its evidence and the date (`/next-up` does it when it finds the evidence); a row is never deleted.

| Change | Items | Waiting for | From whom | Since |
| --- | --- | --- | --- | --- |
| dispatch-ci | 2.2 | a `/spec-dispatch` run in mode `pr` gets a red CI: its line in `docs/dispatch-log.md` | dispatcher | 2026-10-25 |
| add-import | 1.4 | the owner's decision on the CSV dialect | owner | 2026-11-02 |
| release-040 | 3.1 | the GitHub release v0.4.0 is published | owner | 2026-11-10 |
| add-export | 1.2 | the owner's API key of the export service is provided | owner | 2026-11-22 |
| — | — | DESIGN.md: fill in the fields Fonts, Dial | owner | 2026-11-05 |

## Closed

| Change | Items | Waiting for | From whom | Since | Evidence | Closed |
| --- | --- | --- | --- | --- | --- | --- |
| publish-docs | 2.1 | the GitHub release v0.3.0 is published | owner | 2026-10-20 | gh release list: v0.3.0 Latest v0.3.0 | 2026-11-15 |

## Run decisions 2026-11-18 09:16

- add-export: launch now (key: launch)

=== solo-sdd/changes/add-export-blockers/proposal.md
# Proposal

## Why

The add-export change waits for the owner's API key of the export service. Its item 1.2 (the test) cannot be done until the key is given.

## What Changes

- Wait for the owner's API key of the export service; then run the test of add-export 1.2.

=== solo-sdd/changes/add-export-blockers/tasks.md
## 1. Unblock

- [ ] 1.1 The owner gives the API key of the export service
- [ ] 1.2 Connect the key and run the test of add-export 1.2

=== solo-sdd/changes/add-export-blockers/WAITING
The owner's API key of the export service is provided.

=== solo-sdd/changes/add-export-blockers/verification.md
# Verification

Specs: none

=== report
Project: /var/folders/1y/vs_9dysd59d3dz68316ylvnc0000gn/T/waiting-readers.adnl5nc7/project (solo-sdd tree present; `solo-sdd list --json` shows add-export and publish-docs, no numbered changes, so the new change takes the neighbours' unnumbered pattern: `add-export-blockers`).

| Item | Blocker or finding | Where it went | Lift condition |
|---|---|---|---|
| add-export 1.2 (its test) | blocker | new change `add-export-blockers` (proposal.md, tasks.md, WAITING, verification.md); row in the first table of docs/waiting.md | the owner gives the API key of the export service |

Notes:
- No findings were raised beyond the blocker; docs/backlog.md is untouched.
- Item 1.2 is inferred as the blocked item: add-export has only 1.1 done and 1.2 open, and the request names no item.
- Not done: the link to add-export-blockers in add-export/verification.md. That file does not exist, and the change has no "Not Verified" section to link from. Create it, then add the link.
- Not verified: `solo-sdd new add-export-blockers` and `solo-sdd validate`. Both write files, so they must be run by the owner or in a writable session. The spec-plan "Writing rules" were not read, since they live outside the project folder; verification.md above is a minimal placeholder.
- Commit: not made (this session cannot write). Commit the new artifacts separately per the project rules (/ship).
- Next step for the owner: `solo-sdd new add-export-blockers`, copy the files above, validate, commit.
