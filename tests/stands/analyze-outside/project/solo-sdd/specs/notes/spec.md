# notes Specification

## Purpose
Adds, lists and edits short text notes kept in `notes.json`, with every past version of a note.

## Requirements

### Requirement: Add and list
`python3 notes.py add <text>` SHALL store a new note with the next id and print `added <id>`; `python3 notes.py list` SHALL print one line `<id> <text>` per note in id order.

#### Scenario: Two notes
- **WHEN** the user runs `python3 notes.py add "buy milk"`, then `python3 notes.py add "call Ann"`, then `python3 notes.py list`
- **THEN** it prints `1 buy milk` and `2 call Ann`

### Requirement: Edit keeps history
`python3 notes.py edit <id> <text>` SHALL replace the note text and keep the previous text as a past version with its date; `python3 notes.py history <id>` SHALL print every version, the oldest first.

#### Scenario: One edit
- **WHEN** note 1 is `buy milk` and the user runs `python3 notes.py edit 1 "buy oat milk"`, then `python3 notes.py history 1`
- **THEN** it prints `buy milk` and then `buy oat milk`, each with its date
