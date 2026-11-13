---
name: report
description: Use only when the user explicitly invokes /report - "what do we have now", "what is the result", "give a summary of what is done", "what improved this week", "clear statistics are needed", "write what was done, not the commits", "write it all as text".
disable-model-invocation: true
argument-hint: [a period or a topic; the last 7 days by default]
---

# report: a summary for the user

Argument (optional): a period ("for a week", "since 1 October") or a topic ("call scoring"). By default, the last 7 days of this project. The reader is the user.

The report only reads. Files do not change unless the user asked to save the report.

## Sources

- `git log` for the period: group by the result for the product's user, do not retell commits.
- The change archive for the period (`solo-sdd/changes/archive`), their `verification.md`.
- `docs/status.md`, `docs/waiting.md`, `README.md`.
- Project metrics: logs, the database, dashboards, reports. Read only and only free requests.

## Form (in the user's language, as plain text)

1. **Result**: 2-3 sentences: where the project is now and what mattered most in the period.
2. **What was done**, by result: what the product can do now or what got better.
3. **Numbers**: a table. Every number has a source, a date or period and a status: confirmed | from an old record | not checked. A "was → became" comparison, if there is something to compare with. The table always has two rows: archived changes (the `solo-sdd/changes/archive` folders of the period) and `light:` commits (`git log --oneline --grep='^light:' --since=<period start>`), each counted apart.
4. **What is broken or at risk.**
5. **What waits**, from `docs/waiting.md`: what, from whom, since when.
6. **What next**: 1-3 items.

What is not in the sources, do not make up: write "no data" and where to get it.
