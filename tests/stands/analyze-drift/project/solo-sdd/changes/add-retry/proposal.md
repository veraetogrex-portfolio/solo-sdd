# Proposal

## Why

A copy into `backups/` fails now and then while another program holds the folder, and the person has to run `backup.py` again by hand. A second try a moment later almost always works.

## What Changes

- `python3 backup.py <file>` tries a failed copy again, up to the retry limit, and says how many tries it took or that it gave up.
- The retry limit is the setting `process.retry-max` in `backup.json`, default `3`.
- `docs/retry.md` explains the retry and its setting to the person.

## Capabilities

### New Capabilities
- `retry`: a failed copy is tried again up to a limit.

### Modified Capabilities

## Impact

- `backup.py`
- `tests/test_retry.py`
- `docs/retry.md`

## Out of Scope

- A pause between tries: the next change of the plan, `retry-pause`.
- Copying a whole folder.

## Depends On

none

## Source

"When the copy fails I just run it again and it works; let backup do that itself, a few times" (the fixture owner, 20.11.2026)
