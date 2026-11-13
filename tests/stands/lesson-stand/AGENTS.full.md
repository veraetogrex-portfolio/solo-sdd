# shop-handlers

## Purpose and mode

Two async request handlers of a small shop service. Mode: demo.

## Sources of truth

- Contract: `openspec/specs/`; active work: `openspec/changes/`.

## Commands

| What | Command |
|---|---|
| Tests | `python3 -m unittest -v` |
| Specs | `openspec validate --all --strict --no-interactive` |

## Project map

| Path | Role |
|---|---|
| `handlers.py` | Handlers and the in-memory store |
| `test_handlers.py` | Tests of the handlers |

## Delivery

- Git: commit to the current branch; no remote, no push.

## Lessons

- Every money amount is stored in integer cents.
- Every date that crosses a process boundary carries its time zone.
- Every user-facing error message names the failed action and the next step.
- Every list endpoint has a page size limit.
- Every external request has a timeout.
- Every retry has a maximum count and a backoff.
- Every config value is read once at start, not inside a request.
- Every SQL query takes parameters, never string concatenation.
- Every log line about a request carries its request id.
- Every secret is read from the environment, never from a tracked file.
- Every test cleans up the files it creates.
- Every public function validates its input at the boundary.
- Every new dependency is pinned to an exact version.
- Every file write goes to a temporary file first and is renamed into place.
- Every comparison of floats uses a tolerance.
- Every string from a user is escaped before it reaches HTML.
- Every background job is idempotent on a repeat.
- Every lookup that can miss handles the missing case explicitly.
- Every cache entry has an expiry.
- Every feature flag has an owner and a removal date.
