=== docs/waiting.md
# Waiting

What cannot be closed without an external condition. Only the first table waits: when the condition is met, the row moves to the table under `## Closed`, right after this table, with its evidence and the date (`/next-up` does it when it finds the evidence); a row is never deleted.

| Change | Items | Waiting for | From whom | Since |
| --- | --- | --- | --- | --- |
| dispatch-ci | 2.2 | a `/spec-dispatch` run in mode `pr` gets a red CI: its line in `docs/dispatch-log.md` | dispatcher | 2026-10-25 |
| add-import | 1.4 | the owner's decision on the CSV dialect | owner | 2026-11-02 |
| release-040 | 3.1 | the GitHub release v0.4.0 is published | owner | 2026-11-10 |
| — | — | DESIGN.md: fill in the fields Fonts, Dial | owner | 2026-11-05 |
| 3-export-key-blockers | 1.1 | the owner's API key of the export service | owner | 2026-11-22 |

## Closed

| Change | Items | Waiting for | From whom | Since | Evidence | Closed |
| --- | --- | --- | --- | --- | --- | --- |
| publish-docs | 2.1 | the GitHub release v0.3.0 is published | owner | 2026-10-20 | gh release list: v0.3.0 Latest v0.3.0 | 2026-11-15 |

## Run decisions 2026-11-18 09:16

- add-export: launch now (key: launch)
=== report
| add-export key | blocker | 3-export-key-blockers | the owner gives the key |
