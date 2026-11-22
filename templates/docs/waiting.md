# Waiting

What cannot be closed without an external condition. Only the first table waits: when the condition is met, the row moves to the table under `## Closed`, right after this table, with its evidence and the date (`/next-up` does it when it finds the evidence); a row is never deleted.
A change from this table has a `WAITING` file in its folder with one line: what we wait for and a link here. Once its row is in `## Closed`, the owner removes that file on `next-up`'s proposal.
When git does not track this file, a dispatcher run keeps the owner's answers of the run below the table, under `## Run decisions <date> <time>`: one line per answer with the key it gives the planner.

| Change | Items | Waiting for | From whom | Since |
| --- | --- | --- | --- | --- |
