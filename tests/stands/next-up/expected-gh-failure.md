=== docs/waiting.md
# Waiting

What cannot be closed without an external condition. Only the first table waits: when the condition is met, the row moves to the table under `## Closed`, right after this table, with its evidence and the date (`/next-up` does it when it finds the evidence); a row is never deleted.

| Change | Items | Waiting for | From whom | Since |
| --- | --- | --- | --- | --- |
| add-import | 1.4 | the owner's decision on the CSV dialect | owner | 2026-11-02 |
| release-040 | 3.1 | the GitHub release v0.4.0 is published | owner | 2026-11-10 |

## Closed

| Change | Items | Waiting for | From whom | Since | Evidence | Closed |
| --- | --- | --- | --- | --- | --- | --- |
| publish-docs | 2.1 | the GitHub release v0.3.0 is published | owner | 2026-10-20 | gh release list: v0.3.0 Latest v0.3.0 | 2026-11-15 |
| dispatch-ci | 2.2 | a `/spec-dispatch` run in mode `pr` gets a red CI: its line in `docs/dispatch-log.md` | dispatcher | 2026-10-25 | docs/dispatch-log.md:3: 2026-11-12 10:41 dispatch-ci: CI: red \| one SendMessage with the failed lines, then merge | 2026-11-22 |

## Run decisions 2026-11-18 09:16

- add-export: launch now (key: launch)
=== report
Queue:
| # | Item | Source | Why now | Estimate |
|---|---|---|---|---|
| 1 | remove `solo-sdd/changes/publish-docs/WAITING` | docs/waiting.md, `## Closed` row publish-docs | its row is closed | light path |
| 2 | hook errors: 3 in the last 7 days, last: work_hooks claim: OSError [Errno 13] Permission denied: 'CLAIM' | `solo-sdd doctor` | the failure repeats | one change |
| 3 | finish the change add-export (1 of 2 tasks) | `solo-sdd list --json` | half done | one change |
Left out: none
Closed in docs/waiting.md: dispatch-ci - docs/dispatch-log.md:3
Still waiting: 2 rows of the first table
Unread: PRs, issues, CI (`gh` exits 1: error connecting to api.github.com), docs/backlog.md (absent)
Which item to take?
