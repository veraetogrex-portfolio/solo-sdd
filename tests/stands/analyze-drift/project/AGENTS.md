# backup

## Purpose and mode

A tiny command that copies a file into `backups/`: the fixture project of the `analyze-drift` stand.
Mode: demo.

## Sources of truth

- Behaviour contract: `solo-sdd/specs/`; active work: `solo-sdd/changes/`; the project intent: `solo-sdd/project.md`.

## Commands

| What | Command |
|---|---|
| Tests | `python3 -m unittest discover -s tests` |
| Run | `python3 backup.py notes.txt` |
| Specs | `solo-sdd validate --all` |

## Project map

| Path | Role |
|---|---|
| `backup.py` | The command; settings in `backup.json` next to it |
| `tests/test_backup.py` | Tests of the command |
| `solo-sdd/` | Specs, changes and the archive |

## Checks

Before "done": the tests, `solo-sdd validate --all` and the change's live scenario.

## Delivery

- Mode: local
- No remote: nothing is pushed; a finished change is one commit on the local main branch.
- Deploy: no
