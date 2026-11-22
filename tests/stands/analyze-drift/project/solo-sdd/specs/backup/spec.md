# backup Specification

## Purpose
Copies a file into the `backups/` folder next to `backup.py`.

## Requirements

### Requirement: Copy a file
`python3 backup.py <file>` SHALL copy the file into `backups/` under its own name and print `copied <file>`; a copy that fails SHALL print `could not copy <file>: <reason>` to stderr and exit with code 1.

#### Scenario: One file
- **WHEN** the user runs `python3 backup.py notes.txt`
- **THEN** it prints `copied notes.txt`, and `backups/notes.txt` holds the text of `notes.txt`
