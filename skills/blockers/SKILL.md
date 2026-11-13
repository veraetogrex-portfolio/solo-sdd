---
name: blockers
description: Use only when the user explicitly invokes /blockers - "move the blockers into a separate change", "write all blockers out into a separate change", "found outside the change, a separate change is needed", "move it into a separate change and go on".
disable-model-invocation: true
argument-hint: [what to move out; without an argument, all blockers and findings of this work]
---

# blockers: blockers and findings into separate changes, the work goes on

Argument (optional): what exactly to move out. Without an argument collect everything yourself: blockers and findings beyond the current work from this session, the "Not Verified" section in `verification.md` of the current change, the "found outside the change" items from reports.

## Order

1. **List.** For every item: what blocks or what was found, what we wait for (access, the user's decision, data, an external service), who can lift it.
2. **Split.**
   - A blocker: the work exists but waits for an external condition.
   - A finding: work beyond the current specification.
3. **A project with a `solo-sdd/` tree.** Take the number and name by the pattern of the neighbouring changes (`solo-sdd list --json`, the next free number); create each new change with `solo-sdd new <id>`.
   - Blockers of the current change: one new change `<number>-<topic>-blockers`: `proposal.md` (what we wait for and why), `tasks.md` (steps after the condition is lifted), a `WAITING` file with the condition, a line in `docs/waiting.md`. A link to it in `verification.md` of the current change.
   - Findings: one change per independent topic: `proposal.md` and `tasks.md`, without `WAITING`.
   - Every new one: the rest of the artifacts (`verification.md`, deltas or `Specs: none`) by the "Writing rules" of `spec-plan`, then `solo-sdd validate <id>`.
4. **A project without a `solo-sdd/` tree.** If it has `openspec/` instead, name the next step `solo-sdd import openspec` in the report. Blockers go into `docs/waiting.md`, findings into `docs/backlog.md`. No file: create it.
5. **Commit.** The new artifacts in a separate commit by the project rules (`/ship`).
6. **Continuing.** Change the current change only with links. If you were running it, continue from the next item of `tasks.md` without stopping.

## Report (in the user's language)

| Item | Blocker or finding | Where it went | Lift condition |
|---|---|---|---|
