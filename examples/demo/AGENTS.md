# tip

## Purpose and mode

A tiny command-line tip calculator: the demo project of solo-sdd.
Mode: demo.

## Sources of truth

- Behaviour contract: `solo-sdd/specs/`; active work: `solo-sdd/changes/`; the project intent: `solo-sdd/project.md`.

## Commands

| What | Command |
|---|---|
| Tests | `python3 -m unittest discover -s tests` |
| Run | `python3 tip.py 40 15` |
| Specs | `solo-sdd validate --all` |

## Project map

| Path | Role |
|---|---|
| `tip.py` | The command and its arithmetic |
| `tests/test_tip.py` | Tests of the command |
| `solo-sdd/` | Specs, changes and the archive |

## Checks

Before "done": the tests, `solo-sdd validate --all` and the change's live scenario.

## Delivery

- Mode: local
- No remote: `/ship` is not run and nothing is pushed; a finished change is one commit on the local main branch.
- Deploy: no
