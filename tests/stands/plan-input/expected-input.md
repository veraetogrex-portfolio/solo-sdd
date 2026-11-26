# target: input for /spec-plan. Weekly review, 2026-11-23

How to start:
1. Open a new Claude Code (or Codex) session in the folder `{target}`.
2. Type `/spec-plan "{input}"`.
3. When the plan is committed: `/spec-dispatch` in the same session.

Started from any other folder, `/spec-plan` and `/spec-dispatch` find no `solo-sdd/` tree and do nothing.

Only the letter sections are planned; `Already done`, `Already planned`, `Not checked` and `Not decided` are for the owner.

The document is self-contained: the changes are planned from it. Source: the weekly review of 2026-11-20. Facts: from the review.

Suggested slicing: A and B as two light changes.

## A. Raise TIMEOUT to 60 (decision: "yes, all", 2026-11-21)
- Decision: "yes, all", 2026-11-21.
- Facts: 2026-11-18, the review: the line is too short for the slow API.
- Where: `app.py:1`, `TIMEOUT = 30`.
- What: `TIMEOUT = 60`.
- Check: a test that reads `app.TIMEOUT` and gets 60.

## B. Clear CACHE on start (decision: "yes, all", 2026-11-21)
- Decision: "yes, all", 2026-11-21.
- Facts: 2026-11-18, the review: entries survive a restart.
- Where: `app.py:2`, `CACHE = {}`.
- What: a `start()` function that calls `CACHE.clear()`.
- Check: a test that fills the cache, calls `start()` and finds it empty.

## Already done
- Retry once on timeout in app.py: commit {hash-c} `light: retry once on timeout`.
- Drop legacy.py: commit {hash-g} `light: drop legacy.py`.

## Already planned
- Log every retry in app.py: change `log-retries`.

## Not checked
- Drop the cache in worker.py: `worker.py` does not exist in the target.

## Not decided
- Switch to async.
