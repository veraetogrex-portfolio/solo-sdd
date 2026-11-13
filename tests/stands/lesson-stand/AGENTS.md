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
