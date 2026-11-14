# public-tree Specification

## Purpose
The published solo-sdd repository is understandable and usable by a person without access to the owner's computer and projects, and does not disclose them.

## Requirements

### Requirement: No owner traces
The repository's git-tracked files, except `solo-sdd/` and `docs/waiting.md`, SHALL NOT contain owner traces from the requirements Owner path traces, Owner clone path traces and Session and denylist traces; `solo-sdd/specs/` only by the local list (Denylist over main specs). `tests/test_public_tree.py` SHALL check this by `git ls-files` and on a violation print the file, the line number and the found line, then end with code 1. The list itself is not tracked.

#### Scenario: A clean tree
- **WHEN** the tracked files have no home paths, clone paths, session ids and lines from the local list
- **THEN** `python3 tests/test_public_tree.py` ends with code 0

#### Scenario: A forgotten path
- **WHEN** `README.md` has a `cd` command into a folder under `/Users/` with a real user name
- **THEN** the test ends with code 1 and names `README.md`, the line number and the path

#### Scenario: A clone path in a skill
- **WHEN** `skills/project-init/SKILL.md` still has `~/Code/tools/sdd/solo-sdd/templates/`
- **THEN** the test ends with code 1 and names this file

#### Scenario: No list
- **WHEN** there is no file `info/public-denylist.txt`, for example in CI
- **THEN** the test checks only paths and session ids and does not fail because the list is missing

#### Scenario: Unpublished paths
- **WHEN** a line from the local list is only in a file under `solo-sdd/changes/` or in `docs/waiting.md`
- **THEN** the test ends with code 0

#### Scenario: A word inside another word
- **WHEN** the local list has the line `Rok`, and a tracked file has the word `broken`
- **THEN** there is no finding; the word `Rok` in the same file gives code 1

#### Scenario: What the test does not check
- **WHEN** an owner trace is in `tests/test_public_tree.py` itself, under `solo-sdd/changes/` or in `docs/waiting.md`
- **THEN** the test does not check these files: its own content; `solo-sdd/changes/` is the development log; `docs/waiting.md` is not in the index

### Requirement: Only installable code
Every git-tracked file in `global/` and `schema/`, except tests, SHALL be either named in `targets.json` or run by a command described in `README.md` or a `docs/*.md` file git tracks. Every git-tracked skill in `skills/` SHALL be named in `targets.json` and must not require MCP servers or programs that solo-sdd does not install and `README.md` does not name in the requirements.

#### Scenario: A skill with an external server
- **WHEN** a skill works only through an MCP server that is not in the README requirements
- **THEN** the skill is not tracked by git and is not in `targets.json`; the file on disk stays, deployed copies are not deleted

#### Scenario: A single-owner file
- **WHEN** a file is named in `.gitignore` as written for a single owner, except `docs/waiting.md`
- **THEN** it is not in `git ls-files` and in a fresh clone, and in the working folder it stays on disk

#### Scenario: Merging a removal from the index
- **WHEN** a branch that removes such a file from the index is merged into the main folder and the dispatcher runs `sdd-worktree.py transport`
- **THEN** the file lies on the main folder's disk again and is not tracked by git

#### Scenario: A script described in a docs file
- **WHEN** `global/work_hooks_settings.py` is named in no `targets.json` entry and only `docs/first-project.md` describes its command
- **THEN** `tests/test_public_tree.py` passes

### Requirement: License and entry README
The repository root SHALL hold `LICENSE` with the MIT text and the line `Copyright (c) 2026 Vyacheslav Larionov`. `README.md` SHALL start with one or two sentences about what solo-sdd is and for whom, then list the requirements, installation, what goes where, the first step in a project and a link to `ALGORITHM.md`.

#### Scenario: A new reader
- **WHEN** a person without context reads only `README.md`
- **THEN** they can name what is installed into their home folder, and install solo-sdd onto a temporary home folder by the README steps

### Requirement: Owner path traces
The tracked files from the requirement No owner traces SHALL NOT contain absolute paths of home folders (`/Users/<name>/`, `/home/<name>/`), except examples with the placeholder `<user>`, `<name>` or `you` instead of the name.

#### Scenario: A placeholder instead of the name
- **WHEN** `README.md` has the example path `/Users/<user>/project` or `/home/you/project`
- **THEN** there is no finding

### Requirement: Session and denylist traces
The tracked files from the requirement No owner traces SHALL NOT contain:
- agent session ids: the strings `session=<hex>` and `session <hex>`, where `<hex>` is 8 or more hex characters;
- lines from the local list `$(git rev-parse --git-common-dir)/info/public-denylist.txt` (one per line, case-insensitive, as a whole word: `Rok` is not found inside `broken`), if the file exists.

#### Scenario: A session id in text
- **WHEN** `ALGORITHM.md` has the line "in session 3f9a2c1d0b"
- **THEN** the test ends with code 1 and names `ALGORITHM.md`

#### Scenario: The list is case-insensitive
- **WHEN** the local list has the line `Rok`, and a tracked file has the word `ROK`
- **THEN** the test ends with code 1

### Requirement: Owner clone path traces
The tracked files from the requirement No owner traces SHALL NOT contain the owner's clone path (`Desktop/solo-sdd` or `Code/tools/sdd/solo-sdd`) in what is installed or read as documentation: `skills/`, `global/`, `schema/`, `templates/`, `scripts/`, `ALGORITHM.md`, `README.md` (in `solo-sdd/` it is the developer's clone path in a Live Scenario, which is allowed; `solo-sdd/specs/` is cleaned of it together with the change deltas).

#### Scenario: A clone path in solo-sdd
- **WHEN** the developer's clone path stands in a Live Scenario under `solo-sdd/`
- **THEN** it is allowed; `solo-sdd/specs/` is cleaned of it together with the change deltas

### Requirement: Referenced skills exist
Every skill that `skills/*/SKILL.md`, `ALGORITHM.md` or `global/AGENTS.md` names in backquotes as `/name`, `plugin:name` or a hyphenated `name` SHALL be a git-tracked folder in `skills/` or be named in the optional tools list of `README.md` (for `plugin:name`, the plugin). `tests/test_public_tree.py` SHALL fail on any other and name the file, the line and the skill. Backquoted hyphenated words that are not skills (modes, commands, libraries) are listed in the test as such.

#### Scenario: An unshipped skill
- **WHEN** `ALGORITHM.md` has the line "a disputed decision: `my-skill`" and there is no `skills/my-skill/`
- **THEN** the test fails and names `ALGORITHM.md`, the line and `my-skill`

#### Scenario: A skill only on disk
- **WHEN** `skills/my-skill/` lies on disk but is not tracked by git, and `global/AGENTS.md` names `/my-skill`
- **THEN** the test fails and names `global/AGENTS.md` and `my-skill`

#### Scenario: An optional tool
- **WHEN** `debug-profile` mentions `toolbox:trace`, and `README.md` lists toolbox among optional tools
- **THEN** no finding

### Requirement: Denylist over main specs
The local denylist check SHALL also cover the main specs under `solo-sdd/specs/`; archived changes SHALL stay unchecked as history.

#### Scenario: A project name in a spec
- **WHEN** the local list has a project name and a main spec uses it as an example
- **THEN** the test fails and names the spec and the line

#### Scenario: Paths and session ids in a spec
- **WHEN** a main spec has the example `session=157c88ff` and no line from the local list
- **THEN** there is no finding: only the local list covers `solo-sdd/specs/`

### Requirement: Rules name no owner tools
`README.md`, `ALGORITHM.md`, `global/AGENTS.md` and `skills/*/SKILL.md` SHALL NOT name a tool of the owner's own environment (a notes app or its index file, a workflow service, a desktop framework, a chat tool's function); they SHALL name the kind of source instead. The names SHALL be on the local denylist, so No owner traces catches them; a name a kept tracked file holds (a test string of a command form) SHALL stay off the list.

#### Scenario: A notes app in a skill
- **WHEN** the local denylist has `NotesApp`, and `skills/context-resume/SKILL.md` says "start with the index of NotesApp"
- **THEN** `tests/test_public_tree.py` fails and names the file and the line

#### Scenario: A source by kind
- **WHEN** `context-resume` lists its memory sources
- **THEN** it names "a notes vault, if the project names one" and "chat search, if the agent has it"

#### Scenario: A kept test string
- **WHEN** the denylist is filled and `tests/test_work_hooks.py` still holds the desktop framework variable in a command form
- **THEN** `tests/test_public_tree.py` on the real tree ends with code 0

### Requirement: No unsourced citations
`README.md`, `ALGORITHM.md`, `global/AGENTS.md` and `skills/*/SKILL.md` SHALL NOT cite an article, a talk, a paper or a post together with a date and without an `http` address on the same line; such a citation is replaced by the idea itself. `tests/test_public_tree.py` SHALL fail on such a line and name the file and the line.

#### Scenario: A dated article
- **WHEN** `ALGORITHM.md` has a line citing "an article of 22.10.2026" with no address
- **THEN** the test fails and names `ALGORITHM.md` and the line

#### Scenario: A citation with its address
- **WHEN** a skill line cites a post of 2026-10-22 with its `https://` address
- **THEN** no finding

#### Scenario: The idea without the citation
- **WHEN** the rule of `ALGORITHM.md` step 7 is read after this change
- **THEN** it keeps "every handoff between agents loses precision" and names no article

### Requirement: Escaped traces
`tests/test_public_tree.py` SHALL decode the `\xXX`, `\uXXXX` and `\UXXXXXXXX` escapes of each line of a checked file before matching it, so a trace from the requirement No owner traces written with escapes is found and reported like the same trace in plain text.

#### Scenario: An escaped denylisted word
- **WHEN** the local list has the line `Rok`, and a tracked file has `Rok` in a string literal
- **THEN** the test ends with code 1 and names the file, the line number and `Rok`

#### Scenario: An escaped home path
- **WHEN** a tracked file has `/Users/anna/` in a string literal
- **THEN** the test ends with code 1 and names the file

#### Scenario: The real tree
- **WHEN** `python3 tests/test_public_tree.py` runs on the tracked tree with the owner's local list
- **THEN** it ends with code 0
