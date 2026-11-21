## Purpose

Writes all notes with every past version into one ZIP bundle the person can carry to another computer.

## ADDED Requirements

### Requirement: Export to a bundle
`python3 notes.py export <file.zip>` SHALL write a ZIP bundle holding one `notes.json` in the format of the store and print `exported <n> notes to <file.zip>`; an existing `<file.zip>` SHALL be refused with exit code 2 and left unchanged.

#### Scenario: Three notes
- **WHEN** the store has three notes and the user runs `python3 notes.py export out.zip`
- **THEN** it prints `exported 3 notes to out.zip`, and `out.zip` holds one `notes.json` with the three notes

#### Scenario: The file exists
- **WHEN** `out.zip` exists and the user runs `python3 notes.py export out.zip`
- **THEN** it exits with code 2, stderr names `out.zip`, and the file is unchanged

### Requirement: Full history in the bundle
The bundle SHALL hold every note of the store with every past version and its date, whatever the number of notes and versions.

#### Scenario: An edited note
- **WHEN** note 1 was edited twice and the user exports
- **THEN** the bundle's `notes.json` holds the three versions of note 1, the oldest first

### Requirement: Export size
`notes.py export` SHALL always write a bundle of at most 1 MB.

#### Scenario: A usual store
- **WHEN** the store has 200 notes
- **THEN** the bundle is at most 1 MB

### Requirement: Merge an earlier bundle
With `--merge <old.zip>` the export SHALL read the `notes.json` of the ZIP file `<old.zip>` the user names and add its notes to the bundle after the local ones, with new ids from the next local id; a file that is not a ZIP with a `notes.json` SHALL be refused with exit code 2 and no bundle written.

#### Scenario: Two computers
- **WHEN** the store has notes 1 and 2, `old.zip` holds one note, and the user runs `python3 notes.py export out.zip --merge old.zip`
- **THEN** it prints `exported 3 notes to out.zip`, and the note from `old.zip` has id 3

#### Scenario: Not a ZIP
- **WHEN** `old.zip` is a text file
- **THEN** it exits with code 2, stderr names `old.zip`, and `out.zip` is not written

### Requirement: Export date filter
With `--since <YYYY-MM-DD>` the bundle SHALL hold only the notes whose latest version is dated that day or later; a date in another form SHALL be refused with exit code 2.

#### Scenario: Notes since a date
- **WHEN** note 1 was last edited on 2026-11-01 and note 2 on 2026-11-10, and the user runs `python3 notes.py export out.zip --since 2026-11-05`
- **THEN** the bundle holds only note 2
