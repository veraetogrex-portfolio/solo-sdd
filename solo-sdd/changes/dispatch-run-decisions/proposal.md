# Proposal

## Why

The owner's answers during a dispatcher run live only in the dispatcher's context, and a context summary drops them. 2026-11-12, in one project, the owner decided to treat `package-lock.json` and `scripts/build-catalog.mjs` as shared; after a summary the planner got no `--shared` keys, and 4 changes stayed queued until the owner asked "Why did you not do the other changes?" and then "finish all the changes and send them as PRs". 2026-11-09 to 2026-11-13, another project's run had at least 4 summaries in one session. `skills/spec-dispatch/SKILL.md` says the accumulated `--ignore-dep` and `--shared` keys are passed "until the end of the run", but keeps them nowhere outside the context.

## What Changes

- Every owner answer that changes the plan of the run (a shared path, an ignored dependency, a kept marker or dependency, the orchestrator limit, the order, taking or dropping changes) is written at once, before the next recalculation, as one line with the key it gives the planner under the heading `## Run decisions <date> <start time of the run>`.
- The file is `docs/waiting.md` of the main folder when git does not track it, so writing there never makes the main folder unclean for `land-local`; where git tracks it, the same section goes to `solo-sdd/run-decisions.md` inside the git common folder, which git never tracks.
- The run appends its heading at its start, so its section is the last one of the file; after a context summary, before the next recalculation, the dispatcher rereads that last section and passes its keys; earlier runs' sections are not read. A missing `docs/waiting.md` is created from its template.
- The report names the section and its lines.

## Capabilities

### New Capabilities

### Modified Capabilities
- `spec-dispatch`: Run decisions on file and Run decisions after a summary are added.

## Impact

- `skills/spec-dispatch/SKILL.md`
- `templates/docs/waiting.md`
- `tests/test_skill_commands.py`, `tests/stands/run-decisions.py` (new)

## Out of Scope

- Reading the section in `sdd-dispatch-plan.py` itself: the dispatcher passes the keys as before.
- Decisions of `spec-next` or `ship` outside a dispatcher run.
- The other items of the same weekly plan: `reply-language-requests`, `codex-hooks-layout`, `review-rounds-five` and the light path edits.

## Depends On

none

## Source

The owner, 2026-11-15, on the weekly review (translated from Russian), on keeping the dispatcher's run decisions: "Write them to waiting.md".
