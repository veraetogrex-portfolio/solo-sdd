## ADDED Requirements

### Requirement: Test imports found before the run
`python3 tests/run.py` SHALL read the `import` and `from … import` statements directly in the module body of every selected test file and look up the first part of each module name with its own interpreter, with `tests/` and the repository root on the path. A missing one SHALL end the run with code 2, before any file runs, and one line per module: the module, the files that import it, `sys.executable` and the install command.

#### Scenario: An interpreter without hypothesis
- **WHEN** `tests/run.py` runs on an interpreter where `hypothesis` is not installed and a selected file imports it
- **THEN** it ends with code 2, prints `missing module hypothesis` with the importing files, the interpreter path and the install command, and runs no test file

#### Scenario: Only the selected files count
- **WHEN** the runner gets one file whose imports are all found and only an unselected file imports a missing module
- **THEN** the missing module is not reported and the selected file runs

#### Scenario: An import inside a function or under try
- **WHEN** a selected file imports a missing module only inside a function, a class, an `if` or a `try` block
- **THEN** the module is not collected and the file runs

### Requirement: What the import check passes by
A module whose first name part is a `.py` file or a package folder anywhere under `tests/` or directly in the repository root SHALL count as found without a lookup. A file `ast` cannot parse SHALL be left out of the check and run as before. The install command SHALL be the backquoted command of the `Install` row of `AGENTS.md`; when that row cannot be read, the line SHALL say `install command: see the Install row of AGENTS.md`.

#### Scenario: A module of the repository
- **WHEN** a test file imports `skill_text` from `tests/`, `solo_sdd.providers` from the repository root, or `check` of a stand folder it puts on its own path
- **THEN** the module counts as found and the run goes on

#### Scenario: A file that does not parse
- **WHEN** a selected file has a syntax error
- **THEN** the check leaves it out and the file runs and fails with its own output

#### Scenario: No Install row
- **WHEN** a module is missing and `AGENTS.md` has no readable `Install` row
- **THEN** the missing-module line ends with `install command: see the Install row of AGENTS.md`
