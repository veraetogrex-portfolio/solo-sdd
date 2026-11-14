## MODIFIED Requirements

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
