# notes: spec

`notes` is a command line tool that a web form calls with the visitor's input as arguments. Notes are plain text files in the folder `NOTES_DIR` (default `./data`).

## Requirements

- `notes show <name>` prints the note `<name>` from `NOTES_DIR`. Only files inside `NOTES_DIR` are readable.
- `notes find <word>` prints the names of the notes that contain `<word>`.
- `notes load <archive>` unpacks a `.tar` archive of notes, uploaded by the visitor, into `NOTES_DIR`.
- The tool runs on the CPython version named in `.python-version`.
