#!/usr/bin/env python3
"""Red check of the dispatcher: adds two changes to the stand, each green in its own branch,
while after merging both a test fails (the seam).

Usage: python3 tests/stands/red-after-merge.py <stand folder>
The stand is the result of dispatch-stand.sh after the main run: the words command is already in the main spec and the code.
openspec/ is ignored by git, so the changes lie in the folder and are not committed."""
import subprocess
import sys
from pathlib import Path

HEADER = "### Requirement: Word count command"
JSON_SCENARIO = """#### Scenario: JSON mode
- **WHEN** `python3 -m textkit words --json <file>` runs for the same file
- **THEN** `{"words": 3}` is printed, exit code 0
"""

TAIL = """## Needs

none

## Fallback

Not needed: the scenario is fully local.

## Result

<!-- Filled during apply: date, what was run, what was observed. -->

## Not Verified

<!-- Filled during apply: what stayed unproven and why. Write: nothing - if all proven. -->

## Decisions Without Owner

<!-- Filled during apply: choices made without asking, and new changes created for out-of-scope work. -->
"""
ACCEPT = """## 2. Acceptance

- [ ] 2.1 Run the Live Scenario (or its Fallback) from verification.md and record the Result, Not Verified and Decisions Without Owner sections
- [ ] 2.2 Run `openspec validate {id} --strict`, sync delta specs and archive the change with `openspec archive {id} --yes`
"""

JSON = {
    "proposal": """# Proposal

## Why

Scripts find it easier to parse the `words` output as JSON, and a person understands a labelled number better. The default format changes to `words: N`.

## What Changes

- Default output format of `words`: `words: N` instead of a bare number.
- Flag `--json`: `words` prints `{"words": N}`.
- The tests `tests/test_words.py` move to the new format.

## Capabilities

### New Capabilities

None.

### Modified Capabilities
- `words`: requirement "Word count command": a new output format and the `--json` flag

## Impact

- `textkit/commands/words.py`
- `tests/test_words.py`
- `tests/test_words_json.py`

## Out of Scope

- New command `report` (change `words-report`).
- JSON for other commands.

## Depends On

none

## Source

"Make words --json, and by default print `words: N`." (translated)
""",
    "tasks": """## 1. The words format

- [ ] 1.1 Default format `words: N` and flag `--json` in `textkit/commands/words.py` per requirement Word count command; check: unittest in `tests/test_words_json.py` on both scenarios
- [ ] 1.2 Update `tests/test_words.py` to the new format (`words: 3` instead of `3`); check: `python3 -m unittest discover -s tests` is green in the change branch

""" + ACCEPT.format(id="words-json"),
    "verification": """## Live Scenario

1. `printf 'Hello, Wörld! 42\\n' > /tmp/textkit-wj.txt && python3 -m textkit words /tmp/textkit-wj.txt` → prints `words: 3`, code 0.
2. `python3 -m textkit words --json /tmp/textkit-wj.txt` → prints `{"words": 3}`.
3. `python3 -m unittest discover -s tests` → green in the change branch.

Red check of the dispatcher: after merging this change together with `words-report` the test `tests.test_report.ReportTest.test_report_prints_words_line` fails (it expects the old format `3`, and `words` now prints `words: 3`). In the branch of this change the `report` test does not exist yet, so the branch is green.

""" + TAIL,
}

REPORT = {
    "proposal": """# Proposal

## Why

A file summary in one command is needed. For the first version it shows the line that `words` prints.

## What Changes

- New command `report FILE`: prints the same line as `words FILE`.

## Capabilities

### New Capabilities
- `report`: a file summary

### Modified Capabilities

None.

## Impact

- `textkit/commands/report.py`
- `tests/test_report.py`

## Out of Scope

- Other metrics in the summary.
- Editing the `words` command (change `words-json`).

## Depends On

none

## Source

"Make report: a file summary, only words for now, as words prints them." (translated)
""",
    "spec": """## Purpose

A summary of a text file in one command.

## ADDED Requirements

### Requirement: Report command
The command `report FILE` SHALL print to stdout the same line that `words FILE` prints, and exit with the return code of `words`.

#### Scenario: File with words
- **WHEN** the file contains `Hello, Wörld! 42` and `python3 -m textkit report <file>` runs
- **THEN** the same as `words` prints for this file is printed (in the current format, `3`), exit code 0
""",
    "tasks": """## 1. The report command

- [ ] 1.1 Command `report FILE` in `textkit/commands/report.py` (`NAME = "report"`, `run(args)`) per requirement Report command: calls `run` of the `words` command from the registry `textkit.__main__.load()` and returns its code; check: unittest
- [ ] 1.2 The test `tests/test_report.py::ReportTest.test_report_prints_words_line` relies on the current `words` format: expects the output `3` for the file `Hello, Wörld! 42`; check: `python3 -m unittest discover -s tests` is green in the change branch

""" + ACCEPT.format(id="words-report"),
    "verification": """## Live Scenario

1. `printf 'Hello, Wörld! 42\\n' > /tmp/textkit-wr.txt && python3 -m textkit report /tmp/textkit-wr.txt` → prints `3`, code 0.
2. `python3 -m textkit` → the command list has `report`.
3. `python3 -m unittest discover -s tests` → green in the change branch.

Red check of the dispatcher: the test `tests.test_report.ReportTest.test_report_prints_words_line` relies on the current `words` format (a bare number). After merging this change together with `words-json` the `words` command prints `words: 3`, and this test fails; in the branch of this change it is green.

""" + TAIL,
}


def modified_block(spec_text):
    """The words-json MODIFIED block from the current requirement block in the main spec."""
    i = spec_text.index(HEADER)
    j = spec_text.find("\n### Requirement:", i + 1)
    block = spec_text[i:j if j >= 0 else len(spec_text)].strip("\n")
    if "a single number," not in block:
        fail("The requirement \"Word count command\" has no phrase \"a single number,\": do not know what to replace.")
    old = "- **THEN** `3` is printed, exit code 0"
    if old not in block:
        fail("The requirement \"Word count command\" has no scenario with the output `3`.")
    block = block.replace("a single number,", "the line `words: N` (with the `--json` flag, `{\"words\": N}`), where N is", 1)
    block = block.replace(old, "- **THEN** `words: 3` is printed, exit code 0", 1)
    return "## MODIFIED Requirements\n\n" + block + "\n\n" + JSON_SCENARIO


def fail(msg):
    print(msg, file=sys.stderr)
    sys.exit(1)


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main(argv):
    if len(argv) != 1:
        fail("Usage: python3 tests/stands/red-after-merge.py <stand folder>")
    stand = Path(argv[0]).expanduser()
    changes = stand / "openspec" / "changes"
    if not changes.is_dir():
        fail(f"Stand not found: no {changes}. Create it: bash tests/stands/dispatch-stand.sh")
    for cid in ("words-json", "words-report"):
        if (changes / cid).exists() or list((changes / "archive").glob(f"*-{cid}")):
            fail(f"The stand already has change {cid}.")
    words_spec = stand / "openspec" / "specs" / "words" / "spec.md"
    words_text = words_spec.read_text(encoding="utf-8") if words_spec.is_file() else ""
    if HEADER not in words_text:
        fail("The words command is not in the stand's main spec: run the main scenario first (add-words merged and archived).")
    for cid, d, cap in (("words-json", JSON, "words"), ("words-report", REPORT, "report")):
        subprocess.run(["openspec", "new", "change", cid], cwd=stand, check=True, stdout=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
        base = changes / cid
        write(base / "proposal.md", d["proposal"])
        write(base / "specs" / cap / "spec.md", d.get("spec") or modified_block(words_text))
        write(base / "tasks.md", d["tasks"])
        write(base / "verification.md", d["verification"])
    check = subprocess.run(["openspec", "validate", "--all", "--strict", "--no-interactive"], cwd=stand,
                           capture_output=True, text=True, stdin=subprocess.DEVNULL)
    if check.returncode:
        fail(check.stdout + check.stderr + "openspec validate failed.")
    print("Added: words-json, words-report")
    print(f"Next: cd {stand} and run /spec-dispatch")


main(sys.argv[1:])
