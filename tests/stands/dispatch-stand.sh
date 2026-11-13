#!/usr/bin/env bash
# Live Scenario stand of change dispatch-pipeline: a run of the dispatcher skill /spec-dispatch.
# The textkit project (Python CLI) with the OpenSpec solo schema and five open changes:
#   add-words, add-lines, chars-bytes: no dependencies, the first wave;
#   add-top-words: Depends On: add-words, after its merge;
#   chars-empty: changes the same chars requirement as chars-bytes, waits for its merge.
# add-words and add-lines both append a line to the end of the "Commands" section of README.md,
# but neither names README in Impact: the plan puts them in one wave,
# and merging the second gives a conflict in README.md (on purpose, the orchestrator resolves it).
# As in a consumer project, openspec/ and AGENTS.md are in .gitignore: they lie in the folder but not in git.
# Flag --github: a "Delivery" section in AGENTS.md, a CI workflow, a sixth change ci-red (the test passes on
# macOS and fails in CI on Linux because of file name case), a private repository on the owner's
# account, main protection (if the plan allows) and waiting for the first CI run.
# Flag --bare-remote: no "Delivery" section, the remote is a local bare repository <folder>-remote.git next to the stand
# (removed by hand together with the stand). Flag --agents-tracked: the same, and AGENTS.md under git.
# All five changes append a line to the "Stands" table of AGENTS.md (the dispatcher keeps it).
# solo-sdd and global settings do not change; subagent depth 2 is set only in the project.
set -euo pipefail

GITHUB=0
BARE_REMOTE=0
TRACKED=0
POS=()
for a in "$@"; do
  case "$a" in
    --github) GITHUB=1 ;;
    --bare-remote) BARE_REMOTE=1 ;;
    --agents-tracked) BARE_REMOTE=1; TRACKED=1 ;;
    *) POS+=("$a") ;;
  esac
done
if [ "$GITHUB" = 1 ] && [ "$BARE_REMOTE" = 1 ]; then
  echo "--github is incompatible with --bare-remote and --agents-tracked." >&2
  exit 1
fi
DIR="${POS[0]:-$HOME/Desktop/sdd-dispatch-stand}"

if [ -e "$DIR" ] || { [ "$BARE_REMOTE" = 1 ] && [ -e "$DIR-remote.git" ]; }; then
  echo "Folder $DIR or $DIR-remote.git already exists. Delete it or pass another path as the first argument." >&2
  exit 1
fi
command -v openspec >/dev/null || { echo "No openspec in PATH." >&2; exit 1; }
if [ "$GITHUB" = 1 ]; then
  command -v gh >/dev/null || { echo "No gh in PATH." >&2; exit 1; }
fi
if ! openspec schemas 2>/dev/null | grep -q '^ *solo'; then
  echo "The solo schema is not installed (openspec schemas): this OpenSpec-era stand needs a schema built before drop-openspec." >&2
  exit 1
fi

mkdir -p "$DIR"
cd "$DIR"
git init -q -b main
openspec init --tools claude --no-animation . >/dev/null

# ---------------------------------------------------------------- code
mkdir -p textkit/commands tests docs

cat > textkit/__init__.py <<'EOF'
"""textkit: small commands for analysing text files."""
EOF

cat > textkit/__main__.py <<'EOF'
import importlib
import pkgutil
import sys

from textkit import commands


def load():
    registry = {}
    for info in pkgutil.iter_modules(commands.__path__):
        module = importlib.import_module(f"textkit.commands.{info.name}")
        registry[module.NAME] = module.run
    return registry


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    registry = load()
    if not argv or argv[0] not in registry:
        print("usage: python3 -m textkit <command> [args]", file=sys.stderr)
        print("commands: " + ", ".join(sorted(registry)), file=sys.stderr)
        return 2
    return registry[argv[0]](argv[1:]) or 0


if __name__ == "__main__":
    sys.exit(main())
EOF

cat > textkit/commands/__init__.py <<'EOF'
"""Every module of the package is a command: it declares NAME and run(args) -> int."""
EOF

cat > textkit/commands/chars.py <<'EOF'
import sys

NAME = "chars"


def run(args):
    if len(args) != 1:
        print("usage: python3 -m textkit chars FILE", file=sys.stderr)
        return 1
    try:
        with open(args[0], encoding="utf-8") as f:
            text = f.read()
    except FileNotFoundError:
        print(f"file not found: {args[0]}", file=sys.stderr)
        return 1
    print(len(text))
    return 0
EOF

cat > tests/__init__.py <<'EOF'
EOF

cat > tests/test_chars.py <<'EOF'
import io
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

from textkit.__main__ import main


class CharsTest(unittest.TestCase):
    def run_cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(list(args))
        return code, out.getvalue(), err.getvalue()

    def test_counts_characters(self):
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".txt", delete=False) as f:
            f.write("éñ\n")
        try:
            self.assertEqual(self.run_cli("chars", f.name), (0, "3\n", ""))
        finally:
            os.unlink(f.name)

    def test_missing_file(self):
        code, out, err = self.run_cli("chars", "/nonexistent/file.txt")
        self.assertEqual((code, out), (1, ""))
        self.assertIn("/nonexistent/file.txt", err)

    def test_lists_commands(self):
        code, out, err = self.run_cli()
        self.assertEqual(code, 2)
        self.assertIn("chars", err)


if __name__ == "__main__":
    unittest.main()
EOF

cat > sample.txt <<'EOF'
Winter came to the town quietly. Leaves fell on the wet streets, and the town turned gold.
A cat sat at the café window and watched the leaves fall.

In the evening the town lit its lamps, and winter grew warm.
EOF

cat > .gitignore <<'EOF'
__pycache__/
openspec/
AGENTS.md
.claude/worktrees/
.claude/hooks.log
.claude/ctx-report.txt
.env
EOF

cat > README.md <<'EOF'
# textkit

Commands for analysing text files. Python 3.9+, no dependencies.

## Commands

- `python3 -m textkit chars FILE` — number of characters

## Examples

    python3 -m textkit chars sample.txt  # 211
EOF

cat > AGENTS.md <<'EOF'
# textkit

## Purpose and mode

A learning CLI for analysing text files: every command is a separate module in `textkit/commands`.
Mode: demo.

## Sources of truth

Contract: `openspec/specs/`. Active work: `openspec/changes/`. README: how to run.

## Working with specs

- One change per session, up to the archive.
- No clarifying questions: a reasoned decision, recorded in the report.
- Work outside the current spec becomes a new change.
- After `tasks.md` is closed, an independent live test before reporting readiness.

## Commands

| What | Command |
|---|---|
| Install | not needed |
| Tests | `python3 -m unittest discover -s tests -v` |
| Run | `python3 -m textkit <command> FILE` |
| Live run | `python3 -m textkit <command> sample.txt` |
| Specs | `openspec validate --all --strict --no-interactive` |

## Project map

| Path | Role |
|---|---|
| `textkit/__main__.py` | Dispatcher: finds the commands in `textkit/commands` |
| `textkit/commands/*.py` | Commands: `NAME` and `run(args) -> int` |
| `tests/` | unittest, one file per command |
| `sample.txt` | Text for the live run |

## Boundaries and invariants

- A new command is a new module in `textkit/commands`; the dispatcher is not edited.
- Python standard library only.
- Input error: empty stdout, a message in stderr, code 1.

## Stands

| Check | Command |
|---|---|
| chars | `python3 -m textkit chars sample.txt` |

## Checks

Before "done": tests, `openspec validate --all --strict --no-interactive`, a live run of the command on `sample.txt`.

## Security

No secrets and no paid requests.
EOF

echo "@AGENTS.md" > CLAUDE.md

cat > docs/waiting.md <<'EOF'
# Waiting

What cannot be closed without an external condition. The line is removed when the condition is met.
A change from this table has a `WAITING` file in its folder with one line: what we wait for and a link here.

| Change | Items | Waiting for | From whom | Since |
| --- | --- | --- | --- | --- |
EOF

# ---------------------------------------------------------------- openspec: config and main specs
cat > openspec/config.yaml <<'EOF'
schema: solo

context: |
  Language: ru. Keep OpenSpec structural headings and SHALL/MUST keywords in English.
  Mode: demo
  Intent: textkit is a learning CLI for analysing text files; every command is a separate module.
  Success: a command works on sample.txt and is covered by tests, and the dispatcher does not change.

operations:
  apply:
    guidance:
      - Paid calls to the product model in tests and live acceptance run on the cheapest models; review and acceptance run on the main model
      - Readiness is proven by a scenario in what a person gets, not by green unit tests
EOF

mkdir -p openspec/specs/cli openspec/specs/chars
cat > openspec/specs/cli/spec.md <<'EOF'
# cli Specification

## Purpose

textkit entry point: finds the commands in the `textkit/commands` package and runs the chosen one, so new commands are added without editing the dispatcher.

## Requirements

### Requirement: Command discovery
The CLI SHALL find commands by the modules of the `textkit/commands` package: every module declares `NAME` and a function `run(args) -> int`, whose return code becomes the process code.

#### Scenario: Command list
- **WHEN** `python3 -m textkit` runs without arguments
- **THEN** a usage line and the list of all commands go to stderr, exit code 2

#### Scenario: Running a command
- **WHEN** `python3 -m textkit chars sample.txt` runs
- **THEN** the `chars` module runs, its return code becomes the process code
EOF

cat > openspec/specs/chars/spec.md <<'EOF'
# chars Specification

## Purpose

Counting characters in a text file: the simplest estimate of text size.

## Requirements

### Requirement: Character count command
The command `chars FILE` SHALL print to stdout the number of characters of the file in UTF-8 and exit with code 0; if there is no file, empty stdout, a message with the file name in stderr and code 1.

#### Scenario: Ordinary file
- **WHEN** `python3 -m textkit chars sample.txt` runs
- **THEN** `211` is printed, exit code 0

#### Scenario: File not found
- **WHEN** `python3 -m textkit chars none.txt` runs for a file that does not exist
- **THEN** stdout is empty, stderr has a message with the file name, exit code 1
EOF

# ---------------------------------------------------------------- change: add-words
openspec new change add-words >/dev/null
C=openspec/changes/add-words
mkdir -p $C/specs/words
cat > $C/proposal.md <<'EOF'
# Proposal

## Why

Right now textkit counts only characters, and estimating text size needs a word count. Splitting text into words will be needed by the next commands too, so it is worth making it shared.

## What Changes

- New command `words FILE`: prints the number of words in the file.
- Function `tokenize(text)` in `textkit/commands/words.py`: shared splitting of text into words for other commands.
- A line about the command in the "Commands" section of README.md.
- A check line in the "Stands" table of AGENTS.md.

## Capabilities

### New Capabilities
- `words`: counting words in a file and the shared rule of what counts as a word

### Modified Capabilities

None.

## Impact

- `textkit/commands/words.py`
- `tests/test_words.py`
- `AGENTS.md`

## Out of Scope

- Word frequency analysis (change `add-top-words`).
- Reading from stdin and several files at once.

## Depends On

none

## Source

"Add a words command: how many words are in a file. Make the word splitting shared, it will be needed for the top words. And do not forget the line in README." (translated)
EOF
cat > $C/specs/words/spec.md <<'EOF'
## Purpose

Counting words in a text file and one rule for splitting text into words for all textkit commands.

## ADDED Requirements

### Requirement: Word tokenization
The function `tokenize(text)` SHALL return the list of words of the text, where a word is a continuous run of Unicode letters or digits, lowercased; punctuation, underscores and spaces are not words.

#### Scenario: Punctuation and Unicode letters
- **WHEN** `tokenize("Hello, Wörld! 42")` is called
- **THEN** `["hello", "wörld", "42"]` is returned

#### Scenario: Empty text
- **WHEN** `tokenize("")` is called
- **THEN** an empty list is returned

### Requirement: Word count command
The command `words FILE` SHALL print to stdout a single number, the count of words of the file by the `tokenize` rule, and exit with code 0; if there is no file, empty stdout, a message with the file name in stderr and code 1.

#### Scenario: Ordinary file
- **WHEN** the file contains `Hello, Wörld! 42` and `python3 -m textkit words <file>` runs
- **THEN** `3` is printed, exit code 0

#### Scenario: File not found
- **WHEN** `python3 -m textkit words none.txt` runs for a file that does not exist
- **THEN** stdout is empty, stderr has a message with the file name, exit code 1

### Requirement: Words in README
The "Commands" section of README.md SHALL end with the line ``- `python3 -m textkit words FILE` — number of words``.

#### Scenario: Line in README
- **WHEN** README.md is opened
- **THEN** the last line of the "Commands" section is ``- `python3 -m textkit words FILE` — number of words``
EOF
cat > $C/verification.md <<'EOF'
## Live Scenario

1. `printf 'Hello, Wörld! 42\n' > /tmp/textkit-words.txt && python3 -m textkit words /tmp/textkit-words.txt` → prints `3`, code 0.
2. `python3 -m textkit words sample.txt` → prints `41`.
3. `python3 -m textkit words none.txt; echo "exit $?"` → a message with the file name in stderr, `exit 1`.
4. `python3 -m textkit` → the command list has `words`.
5. `grep -n 'textkit words' README.md` → the line is found in the "Commands" section.

## Needs

none

## Fallback

Not needed: the scenario is fully local.

## Result

<!-- Filled during apply: date, what was run, what was observed. -->

## Not Verified

<!-- Filled during apply: what stayed unproven and why. Write: nothing - if all proven. -->

## Decisions Without Owner

<!-- Filled during apply: choices made without asking, and new changes created for out-of-scope work. -->
EOF
cat > $C/tasks.md <<'EOF'
## 1. Splitting and the words command

- [ ] 1.1 `tokenize(text)` in `textkit/commands/words.py` per requirement Word tokenization; check: unittest on both scenarios of the requirement
- [ ] 1.2 Command `words FILE` (`NAME = "words"`, `run(args)`) per requirement Word count command; check: unittest on both scenarios, including exit code and stderr
- [ ] 1.3 Append the line ``- `python3 -m textkit words FILE` — number of words`` to the end of the "Commands" section of README.md (after the last line of the list) per requirement Words in README; check: `grep -n 'textkit words' README.md`
- [ ] 1.4 Append the line ``| words | `python3 -m textkit words sample.txt` |`` to the end of the "Stands" table of AGENTS.md; check: `grep -n 'textkit words' AGENTS.md`

## 2. Acceptance

- [ ] 2.1 Run the Live Scenario (or its Fallback) from verification.md and record the Result, Not Verified and Decisions Without Owner sections
- [ ] 2.2 Run `openspec validate add-words --strict`, sync delta specs and archive the change with `openspec archive add-words --yes`
EOF

# ---------------------------------------------------------------- change: add-lines
openspec new change add-lines >/dev/null
C=openspec/changes/add-lines
mkdir -p $C/specs/lines
cat > $C/proposal.md <<'EOF'
# Proposal

## Why

The number of non-empty lines shows how many paragraphs and entries a text has, and it cannot be derived from the character count. The command is needed for a quick estimate of file structure.

## What Changes

- Function `count_nonempty(text)` in `textkit/commands/lines.py`: the number of non-empty lines of the text.
- New command `lines FILE`: prints the number of non-empty lines of the file.
- A line about the command in the "Commands" section of README.md.
- A check line in the "Stands" table of AGENTS.md.

## Capabilities

### New Capabilities
- `lines`: counting non-empty lines in a file

### Modified Capabilities

None.

## Impact

- `textkit/commands/lines.py`
- `tests/test_lines.py`
- `AGENTS.md`

## Out of Scope

- Counting empty lines and the total number of lines.
- Reading from stdin and several files at once.

## Depends On

none

## Source

"We need a lines command: how many non-empty lines are in a file. Add it to README." (translated)
EOF
cat > $C/specs/lines/spec.md <<'EOF'
## Purpose

Counting non-empty lines in a text file to estimate its structure.

## ADDED Requirements

### Requirement: Non-empty line counting
The function `count_nonempty(text)` SHALL return the number of lines of the text that have at least one non-whitespace character; a last line without a newline counts too.

#### Scenario: Empty and whitespace lines
- **WHEN** `count_nonempty("a\n\n  \nb")` is called
- **THEN** `2` is returned

### Requirement: Non-empty line count command
The command `lines FILE` SHALL print to stdout the number of non-empty lines of the file by the `count_nonempty` rule and exit with code 0.

#### Scenario: Ordinary file
- **WHEN** the file contains the lines `a`, an empty one, a line of two spaces and `b` without a trailing newline, and `python3 -m textkit lines <file>` runs
- **THEN** `2` is printed, exit code 0

### Requirement: Lines missing file
If there is no file, the command `lines` SHALL print empty stdout, a message with the file name in stderr and exit with code 1.

#### Scenario: File not found
- **WHEN** `python3 -m textkit lines none.txt` runs for a file that does not exist
- **THEN** stdout is empty, stderr has a message with the file name, exit code 1

### Requirement: Lines in README
The "Commands" section of README.md SHALL end with the line ``- `python3 -m textkit lines FILE` — number of non-empty lines``.

#### Scenario: Line in README
- **WHEN** README.md is opened
- **THEN** the last line of the "Commands" section is ``- `python3 -m textkit lines FILE` — number of non-empty lines``
EOF
cat > $C/verification.md <<'EOF'
## Live Scenario

1. `printf 'a\n\n  \nb' > /tmp/textkit-lines.txt && python3 -m textkit lines /tmp/textkit-lines.txt` → prints `2`, code 0.
2. `python3 -m textkit lines sample.txt` → prints `3`.
3. `python3 -m textkit lines none.txt; echo "exit $?"` → a message with the file name in stderr, `exit 1`.
4. `python3 -m textkit` → the command list has `lines`.
5. `grep -n 'textkit lines' README.md` → the line is found in the "Commands" section.

## Needs

none

## Fallback

Not needed: the scenario is fully local.

## Result

<!-- Filled during apply: date, what was run, what was observed. -->

## Not Verified

<!-- Filled during apply: what stayed unproven and why. Write: nothing - if all proven. -->

## Decisions Without Owner

<!-- Filled during apply: choices made without asking, and new changes created for out-of-scope work. -->
EOF
cat > $C/tasks.md <<'EOF'
## 1. The lines command

- [ ] 1.1 Function `count_nonempty(text)` in `textkit/commands/lines.py` per requirement Non-empty line counting (a last line without a newline counts too); check: unittest
- [ ] 1.2 Command `lines FILE` (`NAME = "lines"`, `run(args)`) per requirement Non-empty line count command; check: unittest on an ordinary file
- [ ] 1.3 The "file not found" error per requirement Lines missing file: empty stdout, the file name in stderr, code 1; check: unittest
- [ ] 1.4 Append the line ``- `python3 -m textkit lines FILE` — number of non-empty lines`` to the end of the "Commands" section of README.md per requirement Lines in README; check: `grep -n 'textkit lines' README.md`
- [ ] 1.5 Append the line ``| lines | `python3 -m textkit lines sample.txt` |`` to the end of the "Stands" table of AGENTS.md; check: `grep -n 'textkit lines' AGENTS.md`

## 2. Acceptance

- [ ] 2.1 Run the Live Scenario (or its Fallback) from verification.md and record the Result, Not Verified and Decisions Without Owner sections
- [ ] 2.2 Run `openspec validate add-lines --strict`, sync delta specs and archive the change with `openspec archive add-lines --yes`
EOF

# ---------------------------------------------------------------- change: chars-bytes
openspec new change chars-bytes >/dev/null
C=openspec/changes/chars-bytes
mkdir -p $C/specs/chars
cat > $C/proposal.md <<'EOF'
# Proposal

## Why

The character count is not the file size: for letters outside ASCII there are more bytes than characters. Estimating size needs a byte count mode.

## What Changes

- Flag `--bytes` for the `chars` command: prints the number of bytes of the file instead of the number of characters.
- A check line in the "Stands" table of AGENTS.md.

## Capabilities

### New Capabilities

None.

### Modified Capabilities
- `chars`: requirement "Character count command" gets the `--bytes` mode

## Impact

- `textkit/commands/chars.py`
- `tests/test_chars_bytes.py`
- `AGENTS.md`

## Out of Scope

- Behaviour on an empty and a missing file (change `chars-empty`).
- Encodings other than UTF-8.

## Depends On

none

## Source

"Add a --bytes flag to chars: how many bytes are in the file." (translated)
EOF
cat > $C/specs/chars/spec.md <<'EOF'
## MODIFIED Requirements

### Requirement: Character count command
The command `chars [--bytes] FILE` SHALL print to stdout the number of characters of the file in UTF-8, and with the `--bytes` flag the number of bytes of the file, and exit with code 0; if there is no file, empty stdout, a message with the file name in stderr and code 1.

#### Scenario: Ordinary file
- **WHEN** `python3 -m textkit chars sample.txt` runs
- **THEN** `211` is printed, exit code 0

#### Scenario: Byte mode
- **WHEN** the file contains `éñ` and `python3 -m textkit chars --bytes <file>` runs
- **THEN** `4` is printed, exit code 0

#### Scenario: File not found
- **WHEN** `python3 -m textkit chars none.txt` runs for a file that does not exist
- **THEN** stdout is empty, stderr has a message with the file name, exit code 1
EOF
cat > $C/verification.md <<'EOF'
## Live Scenario

1. `printf 'éñ' > /tmp/textkit-bytes.txt && python3 -m textkit chars --bytes /tmp/textkit-bytes.txt` → prints `4`, code 0.
2. `python3 -m textkit chars /tmp/textkit-bytes.txt` → prints `2`.
3. `python3 -m textkit chars --bytes none.txt; echo "exit $?"` → a message with the file name in stderr, `exit 1`.
4. `grep -n 'textkit chars --bytes' AGENTS.md` → the line is found in the "Stands" table.

## Needs

none

## Fallback

Not needed: the scenario is fully local.

## Result

<!-- Filled during apply: date, what was run, what was observed. -->

## Not Verified

<!-- Filled during apply: what stayed unproven and why. Write: nothing - if all proven. -->

## Decisions Without Owner

<!-- Filled during apply: choices made without asking, and new changes created for out-of-scope work. -->
EOF
cat > $C/tasks.md <<'EOF'
## 1. The --bytes mode

- [ ] 1.1 Flag `--bytes` in `textkit/commands/chars.py` per requirement Character count command: the number of bytes of the file; check: unittest in `tests/test_chars_bytes.py` on the "Byte mode" scenario
- [ ] 1.2 Without the flag and for a missing file the behaviour stays as before; check: `python3 -m unittest discover -s tests` (the `tests/test_chars.py` tests pass)
- [ ] 1.3 Append the line ``| chars-bytes | `python3 -m textkit chars --bytes sample.txt` |`` to the end of the "Stands" table of AGENTS.md; check: `grep -n 'textkit chars --bytes' AGENTS.md`

## 2. Acceptance

- [ ] 2.1 Run the Live Scenario (or its Fallback) from verification.md and record the Result, Not Verified and Decisions Without Owner sections
- [ ] 2.2 Run `openspec validate chars-bytes --strict`, sync delta specs and archive the change with `openspec archive chars-bytes --yes`
EOF

# ---------------------------------------------------------------- change: chars-empty
openspec new change chars-empty >/dev/null
C=openspec/changes/chars-empty
mkdir -p $C/specs/chars
cat > $C/proposal.md <<'EOF'
# Proposal

## Why

The behaviour of `chars` on an empty file is not recorded anywhere and not covered by a test: an empty file must give `0`, not an error, and differ from a missing file.

## What Changes

- File reading moves to `read_text(path)` of the module `textkit/textio.py`: returns the text, or `None` if there is no file.
- Requirement "Character count command" explicitly describes an empty file: `0` and code 0.
- A check line in the "Stands" table of AGENTS.md.

## Capabilities

### New Capabilities

None.

### Modified Capabilities
- `chars`: requirement "Character count command" explicitly describes an empty file

## Impact

- `textkit/textio.py`
- `tests/test_chars_empty.py`
- `AGENTS.md`

## Out of Scope

- The `--bytes` mode (change `chars-bytes`).
- Reading from stdin.

## Depends On

none

## Source

"Check chars on an empty file: it must be 0 and code 0, and for a missing one a message and code 1." (translated)
EOF
cat > $C/specs/chars/spec.md <<'EOF'
## MODIFIED Requirements

### Requirement: Character count command
The command `chars FILE` SHALL print to stdout the number of characters of the file in UTF-8 and exit with code 0, including an empty file, for which `0` is printed; if there is no file, empty stdout, a message with the file name in stderr and code 1.

#### Scenario: Ordinary file
- **WHEN** `python3 -m textkit chars sample.txt` runs
- **THEN** `211` is printed, exit code 0

#### Scenario: Empty file
- **WHEN** the file is empty and `python3 -m textkit chars <file>` runs
- **THEN** `0` is printed, exit code 0

#### Scenario: File not found
- **WHEN** `python3 -m textkit chars none.txt` runs for a file that does not exist
- **THEN** stdout is empty, stderr has a message with the file name, exit code 1
EOF
cat > $C/verification.md <<'EOF'
## Live Scenario

1. `: > /tmp/textkit-empty.txt && python3 -m textkit chars /tmp/textkit-empty.txt; echo "exit $?"` → prints `0`, `exit 0`.
2. `python3 -m textkit chars none.txt; echo "exit $?"` → a message with the file name in stderr, `exit 1`.
3. `grep -n 'textkit chars /tmp' AGENTS.md` → the line is found in the "Stands" table.

## Needs

none

## Fallback

Not needed: the scenario is fully local.

## Result

<!-- Filled during apply: date, what was run, what was observed. -->

## Not Verified

<!-- Filled during apply: what stayed unproven and why. Write: nothing - if all proven. -->

## Decisions Without Owner

<!-- Filled during apply: choices made without asking, and new changes created for out-of-scope work. -->
EOF
cat > $C/tasks.md <<'EOF'
## 1. Empty file

- [ ] 1.1 `read_text(path)` in `textkit/textio.py` (the text, or `None` if there is no file); check: unittest in `tests/test_chars_empty.py`
- [ ] 1.2 CLI tests in `tests/test_chars_empty.py` per requirement Character count command: an empty file gives `0` and code 0, a missing one a message and code 1; check: `python3 -m unittest discover -s tests`
- [ ] 1.3 Append the line ``| chars-empty | `python3 -m textkit chars /tmp/textkit-empty.txt` |`` to the end of the "Stands" table of AGENTS.md; check: `grep -n 'textkit-empty' AGENTS.md`

## 2. Acceptance

- [ ] 2.1 Run the Live Scenario (or its Fallback) from verification.md and record the Result, Not Verified and Decisions Without Owner sections
- [ ] 2.2 Run `openspec validate chars-empty --strict`, sync delta specs and archive the change with `openspec archive chars-empty --yes`
EOF

# ---------------------------------------------------------------- change: add-top-words
openspec new change add-top-words >/dev/null
C=openspec/changes/add-top-words
mkdir -p $C/specs/top-words
cat > $C/proposal.md <<'EOF'
# Proposal

## Why

The most frequent words show what a text is about without reading it whole. Word splitting will already be shared after `add-words`, so the command comes down to counting frequencies and printing.

## What Changes

- New command `top N FILE`: prints the N most frequent words of the file with their counts.
- A check line in the "Stands" table of AGENTS.md.

## Capabilities

### New Capabilities
- `top-words`: the frequency list of the words of a file

### Modified Capabilities

None.

## Impact

- `textkit/commands/top.py`
- `tests/test_top.py`
- `AGENTS.md`

## Out of Scope

- Stop words and stemming: "town" and "towns" are different words.
- Reading from stdin and several files at once.

## Depends On

add-words

## Source

"Make top N: the most frequent words of a file, with counts." (translated)
EOF
cat > $C/specs/top-words/spec.md <<'EOF'
## Purpose

The frequency list of the words of a text file, to see quickly what the text is about.

## ADDED Requirements

### Requirement: Top words command
The command `top N FILE` SHALL print the N most frequent words of the file by the `tokenize` rule from `textkit/commands/words.py`, one per line in the format `word<TAB>count`, by descending count, alphabetically for equal counts; if there are fewer than N distinct words, all are printed; exit code 0.

#### Scenario: Frequencies
- **WHEN** the file contains `cat dog cat mouse dog cat` and `python3 -m textkit top 2 <file>` runs
- **THEN** the lines `cat<TAB>3` and `dog<TAB>2` are printed, exit code 0

#### Scenario: Equal frequencies
- **WHEN** the file contains `b a` and `python3 -m textkit top 5 <file>` runs
- **THEN** the lines `a<TAB>1` and `b<TAB>1` are printed, exit code 0

### Requirement: Top words arguments
The command `top` SHALL exit with code 1, empty stdout and a message in stderr if N is not a positive integer or there is no file.

#### Scenario: Invalid N
- **WHEN** `python3 -m textkit top 0 sample.txt` runs
- **THEN** stdout is empty, stderr has a message about N, exit code 1

#### Scenario: File not found
- **WHEN** `python3 -m textkit top 3 none.txt` runs for a file that does not exist
- **THEN** stdout is empty, stderr has a message with the file name, exit code 1
EOF
cat > $C/verification.md <<'EOF'
## Live Scenario

1. `printf 'cat dog cat mouse dog cat\n' > /tmp/textkit-top.txt && python3 -m textkit top 2 /tmp/textkit-top.txt` → two lines: `cat<TAB>3`, `dog<TAB>2`.
2. `python3 -m textkit top 3 sample.txt` → three lines: `the<TAB>7`, `and<TAB>3`, `town<TAB>3`.
3. `python3 -m textkit top 0 sample.txt; echo "exit $?"` → a message about N in stderr, `exit 1`.
4. `python3 -m textkit` → the command list has `top`.

## Needs

none

## Fallback

Not needed: the scenario is fully local.

## Result

<!-- Filled during apply: date, what was run, what was observed. -->

## Not Verified

<!-- Filled during apply: what stayed unproven and why. Write: nothing - if all proven. -->

## Decisions Without Owner

<!-- Filled during apply: choices made without asking, and new changes created for out-of-scope work. -->
EOF
cat > $C/tasks.md <<'EOF'
## 1. The top command

- [ ] 1.1 Command `top N FILE` in `textkit/commands/top.py` (`NAME = "top"`, `run(args)`) per requirement Top words command, splitting through `tokenize` from `textkit.commands.words`; check: unittest on both scenarios
- [ ] 1.2 Argument check per requirement Top words arguments; check: unittest on both scenarios, including exit code and stderr
- [ ] 1.3 Append the line ``| top | `python3 -m textkit top 3 sample.txt` |`` to the end of the "Stands" table of AGENTS.md; check: `grep -n 'textkit top' AGENTS.md`

## 2. Acceptance

- [ ] 2.1 Run the Live Scenario (or its Fallback) from verification.md and record the Result, Not Verified and Decisions Without Owner sections
- [ ] 2.2 Run `openspec validate add-top-words --strict`, sync delta specs and archive the change with `openspec archive add-top-words --yes`
EOF

# ---------------------------------------------------------------- observation: hooks, depth, context report
cat > .claude/log_hook.py <<'EOF'
"""Test logger: every hook event as one JSON line in .claude/hooks.log.
On Stop and SessionEnd of the main agent it recomputes .claude/ctx-report.txt."""
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HERE, "hooks.log")
event = sys.argv[1] if len(sys.argv) > 1 else "?"
try:
    data = json.load(sys.stdin)
except Exception:
    data = {}

rec = {"t": time.strftime("%H:%M:%S"), "event": event, "session": str(data.get("session_id", ""))[:8]}
for k in ("agent_id", "agent_type", "tool_name", "tool_use_id", "stop_hook_active", "source", "reason"):
    if k in data:
        rec[k] = data[k]
if data.get("cwd"):
    rec["cwd"] = os.path.relpath(data["cwd"], os.path.dirname(HERE)) if data["cwd"].startswith(os.path.dirname(HERE)) else data["cwd"]
ti = data.get("tool_input") or {}
tool = data.get("tool_name")
if event == "PreToolUse":
    if tool in ("Agent", "Task"):
        rec["input"] = {k: ti.get(k) for k in ("description", "subagent_type", "model", "isolation", "run_in_background")}
        rec["input"]["prompt_chars"] = len(str(ti.get("prompt", "")))
    elif tool == "SubagentHandback":
        rec["handback"] = json.dumps(ti, ensure_ascii=False)[:2000]
    elif "command" in ti:
        rec["cmd"] = str(ti["command"])[:200]
    elif "file_path" in ti:
        rec["file"] = ti["file_path"]
    elif "skill" in ti:
        rec["skill"] = ti.get("skill")
if event in ("Stop", "SubagentStop"):
    if data.get("background_tasks"):
        rec["background_tasks"] = json.dumps(data["background_tasks"], ensure_ascii=False)[:300]
    if data.get("last_assistant_message"):
        rec["last_message"] = str(data["last_assistant_message"])[:300]
if event in ("SessionStart", "SessionEnd"):
    rec["transcript"] = data.get("transcript_path")

with open(LOG, "a", encoding="utf-8") as f:
    f.write(json.dumps(rec, ensure_ascii=False) + "\n")

if event == "SessionStart":
    print("MARKER-SESSIONSTART-7731: this text was added by the SessionStart hook of the test project.")
if event in ("Stop", "SessionEnd") and not data.get("agent_id") and data.get("transcript_path"):
    subprocess.run([sys.executable, os.path.join(HERE, "ctx_report.py"), data["transcript_path"]],
                   capture_output=True, timeout=30)
EOF

cat > .claude/ctx_report.py <<'EOF'
"""What the main agent's context consists of: its transcript broken down by message kind.
Tokens are a rough estimate by characters (characters / 3.5); the exact context size comes from the usage of the last answer."""
import collections
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
path = sys.argv[1]
chars = collections.Counter()
count = collections.Counter()
names = {}
last_usage = None


def text_of(x):
    if isinstance(x, str):
        return x
    if isinstance(x, list):
        return "".join(text_of(i.get("text", "") if isinstance(i, dict) else i) for i in x)
    return json.dumps(x, ensure_ascii=False)


def add(key, n):
    chars[key] += n
    count[key] += 1


for line in open(path, encoding="utf-8"):
    try:
        e = json.loads(line)
    except Exception:
        continue
    t = e.get("type")
    msg = e.get("message") or {}
    content = msg.get("content")
    if t == "assistant":
        if msg.get("usage"):
            last_usage = msg["usage"]
        for c in content if isinstance(content, list) else []:
            ct = c.get("type")
            if ct == "text":
                add("answers: text", len(c.get("text", "")))
            elif ct == "thinking":
                add("answers: thinking", len(c.get("thinking", "")))
            elif ct == "tool_use":
                names[c.get("id")] = c.get("name")
                add("calls: " + str(c.get("name")), len(json.dumps(c.get("input"), ensure_ascii=False)))
    elif t == "user":
        if isinstance(content, str):
            kind = "service inserts" if content.lstrip().startswith("<") else "owner messages"
            add(kind, len(content))
        for c in content if isinstance(content, list) else []:
            if c.get("type") == "tool_result":
                add("results: " + str(names.get(c.get("tool_use_id"), "?")), len(text_of(c.get("content"))))
            elif c.get("type") == "text":
                txt = c.get("text", "")
                kind = "service inserts" if txt.lstrip().startswith("<") else "owner messages"
                add(kind, len(txt))
    else:
        add("other records (" + str(t) + "), not all go into the context", len(line))

total = sum(v for k, v in chars.items() if not k.startswith("other"))
lines = ["Transcript: " + path]
if last_usage:
    ctx = sum(last_usage.get(k, 0) for k in ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"))
    lines.append("Context at the last answer (usage): %d tokens" % ctx)
lines.append("Session messages: %d characters, ~%d tokens" % (total, total / 3.5))
lines.append("")
lines.append("%-55s %8s %8s %5s" % ("kind", "chars", "~tokens", "count"))
for k, v in chars.most_common():
    lines.append("%-55s %8d %8d %5d" % (k[:55], v, v / 3.5, count[k]))
out = "\n".join(lines) + "\n"
open(os.path.join(HERE, "ctx-report.txt"), "w", encoding="utf-8").write(out)
print(out)
EOF

python3 - <<'EOF'
import json, os
path = ".claude/settings.json"
cfg = json.load(open(path)) if os.path.exists(path) else {}
cfg.setdefault("env", {})["CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH"] = "2"
cmd = lambda ev: [{"hooks": [{"type": "command", "command": 'python3 "$CLAUDE_PROJECT_DIR/.claude/log_hook.py" ' + ev}]}]
hooks = cfg.setdefault("hooks", {})
for ev in ("SessionStart", "SubagentStart", "SubagentStop", "Stop", "SessionEnd"):
    hooks.setdefault(ev, []).extend(cmd(ev))
for ev in ("PreToolUse", "PostToolUse"):
    hooks.setdefault(ev, []).append({"matcher": "*", "hooks": cmd(ev)[0]["hooks"]})
json.dump(cfg, open(path, "w"), ensure_ascii=False, indent=2)
EOF

# ---------------------------------------------------------------- stand check and commit
VALIDATE_OUT="$(mktemp)"
openspec validate --all --strict --no-interactive >"$VALIDATE_OUT" 2>&1 || {
  cat "$VALIDATE_OUT" >&2
  rm -f "$VALIDATE_OUT"
  echo "The stand did not pass openspec validate. Folder left: $DIR" >&2
  exit 1
}
rm -f "$VALIDATE_OUT"
python3 -m unittest discover -s tests -q 2>/dev/null || { echo "Base tests failed." >&2; exit 1; }

if [ "$TRACKED" = 1 ]; then
  grep -vx 'AGENTS.md' .gitignore > .gitignore.tmp
  mv .gitignore.tmp .gitignore
fi
git add -A
git commit -qm "textkit: dispatcher stand"

if [ "$BARE_REMOTE" = 1 ]; then
  BARE="$PWD-remote.git"
  git init -q --bare -b main "$BARE"
  git remote add origin "$BARE"
  git push -qu origin main
  git remote set-head origin main
fi

if [ "$GITHUB" = 1 ]; then
  # ------------------------------------------------------------ --github: the local part
  cat >> AGENTS.md <<'EOF'

## Delivery

- Mode: pr
- Merge: squash
- PR title: the first line of the change commit
- Deploy: no
EOF

  mkdir -p .github/workflows
  cat > .github/workflows/tests.yml <<'EOF'
name: tests
on:
  pull_request:
  push:
    branches: [main]
jobs:
  tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: python3 -m unittest discover -s tests -v
EOF

  openspec new change ci-red >/dev/null
  C=openspec/changes/ci-red
  mkdir -p $C/specs/head
  cat > $C/proposal.md <<'EOF'
# Proposal

## Why

A quick look at a file needs its first lines. The `head` command shows the start of a file without reading it whole.

## What Changes

- New command `head N FILE`: prints the first N lines of the file.
- Test fixture `tests/data/Sample-Head.txt`.

## Capabilities

### New Capabilities
- `head`: the first N lines of a file

### Modified Capabilities

None.

## Impact

- `textkit/commands/head.py`
- `tests/test_head.py`
- `tests/data/Sample-Head.txt`

## Out of Scope

- Reading from stdin and several files at once.
- Negative N.

## Depends On

none

## Source

"Add a command head N FILE: the first N lines of a file. Make the test on the ready fixture." (translated)
EOF
  cat > $C/specs/head/spec.md <<'EOF'
## Purpose

The first lines of a text file for a quick look.

## ADDED Requirements

### Requirement: Head command
The command `head N FILE` SHALL print to stdout the first N lines of the file and exit with code 0; if there are fewer than N lines, all are printed; if N is not a positive integer or there is no file, empty stdout, a message in stderr and code 1.

#### Scenario: First lines
- **WHEN** the file contains the lines `a`, `b`, `c` and `python3 -m textkit head 2 <file>` runs
- **THEN** the lines `a` and `b` are printed, exit code 0

#### Scenario: File not found
- **WHEN** `python3 -m textkit head 2 none.txt` runs for a file that does not exist
- **THEN** stdout is empty, stderr has a message with the file name, exit code 1
EOF
  cat > $C/verification.md <<'EOF'
## Live Scenario

1. `printf 'a\nb\nc\n' > /tmp/textkit-head.txt && python3 -m textkit head 2 /tmp/textkit-head.txt` → lines `a`, `b`, code 0.
2. `python3 -m textkit head 2 none.txt; echo "exit $?"` → a message with the file name in stderr, `exit 1`.
3. `python3 -m textkit` → the command list has `head`.

## Needs

none

## Fallback

Not needed: the scenario is fully local.

## Result

<!-- Filled during apply: date, what was run, what was observed. -->

## Not Verified

<!-- Filled during apply: what stayed unproven and why. Write: nothing - if all proven. -->

## Decisions Without Owner

<!-- Filled during apply: choices made without asking, and new changes created for out-of-scope work. -->
EOF
  cat > $C/tasks.md <<'EOF'
## 1. The head command

- [ ] 1.1 Command `head N FILE` in `textkit/commands/head.py` (`NAME = "head"`, `run(args)`) per requirement Head command; put the fixture in `tests/data/Sample-Head.txt` (five lines: `one`, `two`, `three`, `four`, `five`); check: `python3 -m textkit head 2 tests/data/Sample-Head.txt`
- [ ] 1.2 Test `tests/test_head.py`: the "First lines" scenario on the ready fixture: open the file at the path `tests/data/sample-head.txt` (the path from the command name in lower case, like the other tests), N=2, expect `one` and `two`; plus the "File not found" scenario; check: `python3 -m unittest discover -s tests`

## 2. Acceptance

- [ ] 2.1 Run the Live Scenario (or its Fallback) from verification.md and record the Result, Not Verified and Decisions Without Owner sections
- [ ] 2.2 Run `openspec validate ci-red --strict`, sync delta specs and archive the change with `openspec archive ci-red --yes`
EOF
  openspec validate --all --strict --no-interactive >/dev/null 2>&1 || { echo "The stand with ci-red did not pass openspec validate. Folder: $DIR" >&2; exit 1; }
  git add -A
  git commit -qm "textkit: CI and delivery through PR"

  # ------------------------------------------------------------ --github: network
  OWNER="$(gh api user --jq .login)"
  NAME="sdd-dispatch-stand-$(date +%F)"
  if gh repo view "$OWNER/$NAME" >/dev/null 2>&1; then
    echo "Repository $OWNER/$NAME already exists. Not overwriting: delete it (gh repo delete $OWNER/$NAME) or run the stand on another day." >&2
    exit 1
  fi
  gh repo create "$NAME" --private --source . --remote origin --push
  if echo '{"required_status_checks":{"strict":true,"contexts":[]},"enforce_admins":false,"required_pull_request_reviews":null,"restrictions":null}' \
    | gh api -X PUT "repos/$OWNER/$NAME/branches/main/protection" --input - >/dev/null; then
    echo "main protection enabled."
  else
    echo "Warning: branch protection is not available on the plan; continuing without it." >&2
  fi

  RUN_ID=""
  for _ in $(seq 1 30); do
    RUN_ID="$(gh run list --branch main --limit 1 --json databaseId,status,conclusion 2>/dev/null \
      | python3 -c 'import json,sys; r=json.load(sys.stdin); print(r[0]["databaseId"] if r else "")' 2>/dev/null || true)"
    [ -n "$RUN_ID" ] && break
    sleep 10
  done
  [ -n "$RUN_ID" ] || { echo "CI main: no run appeared within 5 minutes." >&2; exit 1; }
  if gh run watch "$RUN_ID" --exit-status >/dev/null 2>&1; then
    echo "CI main: success"
  else
    echo "CI main: failure" >&2
    exit 1
  fi
fi

echo "Done: $DIR"
echo "  change: $(openspec list --json 2>/dev/null | python3 -c 'import json,sys; print(", ".join(c["name"] for c in json.load(sys.stdin).get("changes", [])))' 2>/dev/null || echo 'see openspec list')"
echo
echo "Run:"
echo "  cd $DIR && claude --model sonnet"
echo "  then the command /spec-dispatch"
echo "  Hooks log: $DIR/.claude/hooks.log, context report: $DIR/.claude/ctx-report.txt"
if [ "$GITHUB" = 1 ]; then
  echo
  echo "Repository: https://github.com/$OWNER/$NAME (private)."
  echo "The owner deletes it: gh repo delete $OWNER/$NAME"
fi
if [ "$BARE_REMOTE" = 1 ]; then
  echo
  echo "Remote: $BARE. No \"Delivery\" section; AGENTS.md $([ "$TRACKED" = 1 ] && echo 'under git' || echo 'ignored by git')."
fi
