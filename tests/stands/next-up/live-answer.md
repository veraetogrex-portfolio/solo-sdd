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
| publish-docs | 2.1 | the GitHub release v0.3.0 is published | owner | 2026-10-20 | `gh release list: v0.3.0 Latest v0.3.0 2026-11-01T10:00:00Z` | 2026-11-22 |
| dispatch-ci | 2.2 | a `/spec-dispatch` run in mode `pr` gets a red CI: its line in `docs/dispatch-log.md` | dispatcher | 2026-10-25 | `docs/dispatch-log.md:3: 2026-11-12 10:41 dispatch-ci: CI: red \| one SendMessage with the failed lines, then merge` | 2026-11-22 |

## Run decisions 2026-11-18 09:16

- add-export: launch now (key: launch)

=== report
Queue:
| # | Item | Source | Why now | Estimate |
|---|---|---|---|---|
| 1 | Remove `solo-sdd/changes/publish-docs/WAITING` | `docs/waiting.md` Closed row publish-docs; `solo-sdd/changes/publish-docs/WAITING` | row was closed just now (release v0.3.0 is out) | light path |
| 2 | Hook errors: 3 in 7 days; last `2026-11-22T18:37:12 work_hooks claim: OSError [Errno 13] Permission denied: 'CLAIM'` | `solo-sdd doctor`, hook errors line | the failure repeats | light path |
| 3 | #7 Close the waiting lines and start add-import | issue #7 | open issue | plan |
| 4 | add-export (open change, tasks 1/2, no claim) | `solo-sdd list --json` | open change without a claim | one change |
| 5 | Product search ignores accents: "cafe" does not find "café" | `docs/backlog.md:3` | noted since `/blockers` 2026-11-05 | light path |
Left out: Prices with three decimals round wrong in the cart total (`docs/backlog.md:4`)
Closed in docs/waiting.md: publish-docs (2.1) - `gh release list: v0.3.0 Latest v0.3.0 2026-11-01T10:00:00Z`; dispatch-ci (2.2) - `docs/dispatch-log.md:3: 2026-11-12 10:41 dispatch-ci: CI: red`
Still waiting: 2 rows of the first table
Unread: gh pr list (output cut, not the JSON asked for) | none otherwise
Which item to take?
