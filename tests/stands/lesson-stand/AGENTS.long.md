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
- Every retry has a maximum count and a backoff, a job that retries a paid call stops after the third failure and writes the amount it spent to the log, a webhook handler answers within two seconds and moves its work to a queue, a queue consumer acknowledges a message only after its side effect is stored, a nightly export writes into a temporary table and swaps it in within one transaction, a report that sums money reads every amount from one snapshot, an import of a supplier file refuses a row with an unknown currency instead of skipping it, a price shown to a buyer is the price charged at checkout even when the catalogue changes in between, a discount code is checked for its owner, its expiry and its remaining uses in the same transaction that spends it, a refund goes back to the payment it came from and never to a balance the buyer did not choose, an order that changes state writes the old and the new state with the actor's id, and an e-mail to a buyer is sent only after the transaction that triggers it is committed, since a rolled-back order must never send a receipt.
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
