# Proposal

## Why

The notes live in one `notes.json` on one computer. A person who moves to a new computer, or wants a copy before a disk change, has no way to take the notes with their past versions: copying `notes.json` by hand misses nothing today, but the person does not know where the file is.

## What Changes

- `python3 notes.py export <file.zip>` writes a snapshot of all notes into a ZIP file: one `notes.json` inside, every note with every past version.
- `--merge <old.zip>` also puts the notes of a snapshot made earlier, for example on another computer, into the new one, with new ids after the local ones.
- `--since <date>` takes only the notes changed on that date or later.
- The snapshot is at most 1 MB, so it fits into a mail attachment.

## Capabilities

### New Capabilities
- `export`: a snapshot of the notes into one ZIP file.

### Modified Capabilities

## Impact

- `notes.py`
- `tests/test_export.py`

## Out of Scope

- Reading a snapshot back into `notes.json`: the next change of the plan, `import-snapshot`.
- Encrypting the snapshot.

## Depends On

none

## Source

"I want to take my notes with all their versions to the new laptop, as one file I can mail to myself" (the fixture owner, 15.11.2026)
