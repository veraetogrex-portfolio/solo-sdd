# cli Specification

## Purpose
One command `solo-sdd` installs the solo-sdd process into a person's home folder, shows its state, updates, checks and removes it, without breaking what was there before the installation.

## Requirements

### Requirement: Entry point
The `solo_sdd` package SHALL run as `solo-sdd` (the `pyproject.toml` entry point) and as `python3 -m solo_sdd` on Python 3.9+ without third-party dependencies. The data (`skills/`, `global/`, `schema/`, `templates/`, `targets.json`, `ALGORITHM.md`) SHALL be found both from an installed wheel and from a repository clone. `solo-sdd --version` prints the version from `solo_sdd.__version__`. Without a command or with an unknown one, the command list is printed and code 2 returned.

#### Scenario: From a wheel
- **WHEN** the package is installed with `pip install .` into a temporary environment, and the clone is deleted after that
- **THEN** `solo-sdd status` prints the state of all copies from `targets.json`

#### Scenario: From a clone
- **WHEN** `python3 -m solo_sdd status` is run in a clone
- **THEN** the output after the first line `source: …` matches the output of `python3 sync.py status`

### Requirement: Managed rules block
Copies with `"mode": "block"` in `targets.json` (global rules) SHALL be kept as a block between the lines `<!-- solo-sdd:begin -->` and `<!-- solo-sdd:end -->`. The deployment changes only the block content, `status` and `drift` are computed by the block, and the bytes outside the block are kept as they were, including `\r\n` newlines. A marker is a whole line; the same substring inside a line of text is not a marker. A file not in UTF-8 is `unreachable` and does not change.

#### Scenario: A person's own rules
- **WHEN** `~/.claude/CLAUDE.md` holds a person's own rules without markers
- **THEN** after `install` its text at the start of the file is unchanged, the solo-sdd block is at the end

#### Scenario: Migrating the owner's deployment
- **WHEN** `~/.claude/CLAUDE.md` is entirely equal to the last deployment of `global/AGENTS.md`
- **THEN** after `install` the file consists of one block with the same text, `status` is `ok`, there is no backup

#### Scenario: An edit inside the block
- **WHEN** a person changed a line inside the block
- **THEN** `status` shows `drift`, `install` does not touch the block, `sync pull global/AGENTS.md` pulls the block content into the repository

#### Scenario: Broken markers
- **WHEN** the rules file has only `<!-- solo-sdd:begin -->` without an end
- **THEN** `status` shows `drift`, `install`, `install` with `--force` through `sync.py push --force` and `uninstall` leave the file byte for byte and name it

#### Scenario: A foreign file is not pulled
- **WHEN** a copy is in the `first` state without markers
- **THEN** `sync pull global/AGENTS.md` does not take it: foreign rules do not get into the repository

#### Scenario: No rules file
- **WHEN** a copy file with `"mode": "block"` does not exist
- **THEN** it is created from one block

#### Scenario: The last deployment with a new source text
- **WHEN** there are no markers, the file entirely matches the last deployment (a hash in the state), and the source text has changed since
- **THEN** the file is replaced by a block with the current source text, the state is `ok`; a backup is saved, because the file text differs from the source

#### Scenario: A foreign file without a state entry
- **WHEN** there are no markers and no state entry
- **THEN** the file is foreign: the block is appended at the end after an empty line, the previous text is saved into a backup

#### Scenario: An entry exists, the text differs
- **WHEN** there are no markers, the state entry exists, and the file text differs
- **THEN** `drift`, as for an ordinary copy edited in place; `--force` appends the block, the file text is kept

#### Scenario: Markers erased after the deployment
- **WHEN** the block already stood in this file (an entry in `_blocks`), and the markers are erased
- **THEN** the file counts as having broken markers: personal rules do not get into the repository

#### Scenario: Markers in reverse order or more than one pair
- **WHEN** the markers are broken: only one, in reverse order or more than one pair
- **THEN** `drift`; neither `push`, nor `push --force`, nor `pull`, nor `uninstall` changes such a file, it is named in the output

#### Scenario: A marker inside a line
- **WHEN** a line of text holds `<!-- solo-sdd:begin -->` as a substring among other text
- **THEN** it is not a marker

#### Scenario: A file not in UTF-8
- **WHEN** the rules file is not in UTF-8
- **THEN** the state is `unreachable`, the file does not change

### Requirement: Hooks opt-in
`solo-sdd install --hooks` SHALL connect the `work_hooks.py` hooks, `statusLine`, the `autoMode` rule and `env.CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH=2` in `~/.claude/settings.json` as `work_hooks_settings.py` does, save a settings backup (`settings.json.bak-<time>`, an occupied name is not overwritten) and record in `_hooks` only what this run added. `global/work_hooks_settings.py` SHALL do the same as `install --hooks`, only without the deployment.

#### Scenario: Without the flag
- **WHEN** `solo-sdd install` is run
- **THEN** `~/.claude/settings.json` is not changed

#### Scenario: The depth is set by a person
- **WHEN** `settings.json` already has `"CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH": "3"`
- **THEN** after `install --hooks` the value is `3`, `_hooks` has no variable

#### Scenario: Broken settings
- **WHEN** `settings.json` is truncated and does not parse as JSON
- **THEN** the deployment is done, the settings file is byte for byte the same, the line `fail settings:`, exit code 1

#### Scenario: Everything already connected
- **WHEN** `install --hooks` is run, and everything is already connected
- **THEN** the file is not written, there is no backup, `_hooks` does not change

#### Scenario: No settings file
- **WHEN** there is no `~/.claude/settings.json`
- **THEN** `install --hooks` creates it, `uninstall` then deletes it

#### Scenario: Settings of the wrong kind
- **WHEN** `settings.json` cannot be read, does not parse as JSON, or its top level, `hooks`, `env`, `autoMode` are not objects
- **THEN** `fail settings: <reason>` is printed, the file does not change, exit code 1

#### Scenario: Install without the flag does not read the settings
- **WHEN** `solo-sdd install` is run without `--hooks`
- **THEN** `settings.json` is neither read nor written

### Requirement: Uninstall restores
`solo-sdd uninstall` SHALL delete copies whose content matches the last deployment (with emptied skill folders), remove the block from rules files (a file that was only the block is deleted), remove from `settings.json` exactly what `_hooks` recorded (with a backup), and delete the deployment keys from the state, except the entries of kept copies: a repeated `install` sees them as `drift` and does not overwrite the edit.

#### Scenario: Back as it was
- **WHEN** before the installation a person had their own `CLAUDE.md` and their own hook in `settings.json`
- **THEN** after `install --hooks` and `uninstall` both files match the originals byte for byte

#### Scenario: An edited skill
- **WHEN** the copy `~/.codex/skills/spec-next/SKILL.md` was edited in place
- **THEN** `uninstall` kept it and named it in the output, the other copies are deleted

#### Scenario: A kept copy on a repeated installation
- **WHEN** after `uninstall` a copy with `drift` remained together with its state entry, and `install` is run
- **THEN** `install` sees it as `drift` and does not overwrite the edit

#### Scenario: Settings cannot be read on removal
- **WHEN** on `uninstall` `settings.json` cannot be read or parsed
- **THEN** `fail settings:`, exit code 1, `_hooks` stays for a repeat

#### Scenario: Removal without purge
- **WHEN** `uninstall` is run without `--purge`
- **THEN** `~/.local/share/openspec/schemas/solo` stays: projects refer to it

#### Scenario: Removal with purge
- **WHEN** `uninstall --purge` is run and the data folder holds only what solo-sdd wrote there
- **THEN** `~/.local/share/openspec/schemas/solo` and `~/.local/share/solo-sdd/` are also deleted

#### Scenario: Purge with an owner integration
- **WHEN** `~/.local/share/solo-sdd/integrations/demo/integration` exists and `uninstall --purge` is run after `install`
- **THEN** that file is still there, a `kept` line names `~/.local/share/solo-sdd/integrations`, `state.json`, `ALGORITHM.md` and `templates/` are gone, exit code 0

### Requirement: Status and update
`solo-sdd update` SHALL repeat the deployment from the current `ROOT` and print as the last line the update command of the package itself for the way it was installed (`uv tool upgrade solo-sdd`, `pipx upgrade solo-sdd`, `npm update -g solo-sdd`, `git pull` in a clone, otherwise `python3 -m pip install --upgrade solo-sdd`); this line is printed even with exit code 1.

#### Scenario: Update from uv
- **WHEN** the package is installed with `uv tool install`
- **THEN** the last line of `update` is `uv tool upgrade solo-sdd`

#### Scenario: Update with other installation ways
- **WHEN** the package is installed through pipx, through npm, runs from a clone or is installed otherwise
- **THEN** the last line of `update` is respectively `pipx upgrade solo-sdd`, `npm update -g solo-sdd`, `git pull` in the clone, otherwise `python3 -m pip install --upgrade solo-sdd`

### Requirement: Algorithm and templates layout
`solo-sdd install` SHALL deploy `ALGORITHM.md` to `~/.local/share/solo-sdd/ALGORITHM.md` and every file of `templates/` to `~/.local/share/solo-sdd/templates/` with the same relative path, by the deployment rules (`drift` is not overwritten). Skills and global rules SHALL refer to the algorithm and templates only by these paths.

#### Scenario: Templates after installation
- **WHEN** `solo-sdd install` is run on a clean home folder
- **THEN** `~/.local/share/solo-sdd/templates/solo-sdd/project.md` and `~/.local/share/solo-sdd/ALGORITHM.md` exist, and `grep -rE "Desktop/solo-sdd|Code/tools/sdd/solo-sdd"` over the deployed skills and rules finds nothing

### Requirement: Uninstall round trip
For any initial content of rules files and `settings.json` without solo-sdd markers, the sequence `install --hooks`, then `uninstall` SHALL return them byte for byte. If the settings after removal are equal in meaning to the settings before installation, the file is restored from the `install` backup byte for byte: `install` rewrites `settings.json` with its own formatting. If a person changed the settings after installation, the rest of their content is kept.

#### Scenario: Settings rewritten by install formatting
- **WHEN** `install --hooks` rewrote `settings.json` with its own formatting, and `uninstall` removed exactly what `_hooks` recorded
- **THEN** the file is restored from the `install` backup byte for byte

#### Scenario: A person changed the settings after installation
- **WHEN** after `install --hooks` a person added their own key to `settings.json`
- **THEN** `uninstall` removes what `_hooks` recorded, the person's key stays

### Requirement: Sync pull through the package
`solo-sdd sync pull` SHALL work as `sync.py pull`; if the source is an installed package, not a clone, it also prints that the edit will be lost on update.

#### Scenario: Pull from an installed package
- **WHEN** `solo-sdd sync pull` is run, and the source is an installed package
- **THEN** the edit is pulled as by `sync.py pull`, and it is printed that it will be lost on update

### Requirement: Uninstall keeps edited copies
Copies with `drift` on `solo-sdd uninstall` SHALL stay and be listed; copies without a state entry are not touched.

#### Scenario: A copy without a state entry
- **WHEN** the skills folder holds a file that is not in the deployment state, and `uninstall` is run
- **THEN** the file is in place and unchanged

#### Scenario: An edited copy is named
- **WHEN** a copy was edited in place after the deployment, and `uninstall` is run
- **THEN** the copy stayed and is listed in the output

### Requirement: Status source line
`solo-sdd status` SHALL print the same as `sync.py status`, and as the first line `source: <path> <version>` from `_source` and `_version` of the state, and if there was no deployment yet, the current `ROOT` and `__version__`.

#### Scenario: Status before the first deployment
- **WHEN** `solo-sdd status` is run, and there was no deployment yet
- **THEN** the first line is `source: <ROOT> <__version__>` with the current `ROOT`, then the output of `sync.py status`

### Requirement: Doctor setup checks
`solo-sdd doctor` SHALL also check and print one line `ok|warn|fail <what>: <detail>` each: if `_hooks` exists, the hook entries are in place (otherwise `fail`), if not, `ok hooks: not connected`; `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH` at least 2 (lower or unset: `warn` with `solo-sdd install --hooks`); `_source` matches the current `ROOT` (otherwise or if missing: `warn`); `gh` (missing: `warn`: needed for `ship` and `spec-dispatch`).

#### Scenario: Hooks
- **WHEN** `_hooks` is in the state, but the hook entries are not in place, or there is no `_hooks`
- **THEN** in the first case `fail`, in the second `ok hooks: not connected`

#### Scenario: Subagent depth
- **WHEN** `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH` is below 2 or not set
- **THEN** `warn` with the command `solo-sdd install --hooks`

#### Scenario: The source and gh
- **WHEN** `_source` is missing or does not match the current `ROOT`, or there is no `gh`
- **THEN** `warn` for each; for `gh`, that it is needed for `ship` and `spec-dispatch`

### Requirement: Doctor rules size
`solo-sdd doctor` SHALL sum the bytes of the project instructions Codex loads in the current folder — from the git root down to it, per folder the first existing file of `AGENTS.override.md`, `AGENTS.md` and the plain file names from `project_doc_fallback_filenames`, unless it is blank — and compare the sum with `project_doc_max_bytes` from `$CODEX_HOME/config.toml`, 32768 when unset. The global file in `$CODEX_HOME` is outside this budget.

#### Scenario: Default limit passed
- **WHEN** `config.toml` has no `project_doc_max_bytes` and the project files sum to 33,000 bytes
- **THEN** the line starts with `fail rules-size:`, says that Codex drops everything after 32768 bytes, and the exit code is 1

#### Scenario: Raised limit
- **WHEN** `config.toml` sets `project_doc_max_bytes = 65536` and the project files sum to 33,000 bytes
- **THEN** the line starts with `ok rules-size:`

#### Scenario: Close to the limit
- **WHEN** the project files sum to 80% of the limit or more, up to the limit itself
- **THEN** the line starts with `warn rules-size:`

#### Scenario: Global file outside the budget
- **WHEN** the global `AGENTS.md` is 30,000 bytes and the project files sum to 3,000 bytes
- **THEN** the line starts with `ok rules-size: 3000 of 32768 bytes`

#### Scenario: Override and fallback
- **WHEN** a folder holds both `AGENTS.override.md` and `AGENTS.md`, and another folder holds only a file named in `project_doc_fallback_filenames`
- **THEN** only `AGENTS.override.md` is counted for the first folder and the fallback file for the second

#### Scenario: Fallback entry that is not a file name
- **WHEN** `project_doc_fallback_filenames` holds an empty name, `.`, `..` or a name with `/`
- **THEN** that entry is ignored

#### Scenario: Blank project file
- **WHEN** a project folder holds an `AGENTS.override.md` that is empty or only whitespace and a non-empty `AGENTS.md`
- **THEN** nothing is counted for that folder

#### Scenario: Blank global override
- **WHEN** `$CODEX_HOME/AGENTS.override.md` is empty or only whitespace and `$CODEX_HOME/AGENTS.md` is not
- **THEN** `$CODEX_HOME/AGENTS.md` is named as the global file

#### Scenario: No Codex instructions
- **WHEN** no project file and no global file is found
- **THEN** the line is `ok rules-size: no Codex instructions found`

#### Scenario: Project instructions disabled
- **WHEN** `config.toml` sets `project_doc_max_bytes = 0`
- **THEN** the line starts with `warn rules-size:` and says that Codex loads no project instructions

#### Scenario: Outside a git repository
- **WHEN** `doctor` runs in a folder without a git root
- **THEN** only the current folder's file is counted

#### Scenario: Unreadable config
- **WHEN** `$CODEX_HOME/config.toml` is not valid TOML, or the two keys have values of the wrong type
- **THEN** the limit is 32768 without fallback names and the line says `config.toml unreadable`

### Requirement: Doctor rules size detail
The `rules-size` line SHALL name the project total, the limit and every counted project file with its bytes, largest first, so the owner sees which file to shorten; then the global file with its bytes, marked as outside the budget.

#### Scenario: Two files
- **WHEN** the global file is 9,000 bytes and the project `AGENTS.md` is 20,000 bytes
- **THEN** the line reads `20000 of 32768 bytes`, lists the project file with 20000, then the global file with 9000 and `outside the budget`

### Requirement: Install without schema
`solo-sdd install` SHALL deploy skills and files by `targets.json` by the rules of `sync.py push` (`drift` is not overwritten, a backup is saved before overwriting) and write `_source` (the absolute path of `ROOT`) and `_version` into the state. It SHALL NOT call `openspec` or build a schema. Copies of `openspec-after-update.py` and its test from an earlier version SHALL be removed if unchanged since their deployment, otherwise kept and named.

#### Scenario: A clean home folder
- **WHEN** the home folder has no copy, and there is no `openspec` anywhere
- **THEN** all copies are created, exit code 0, no line mentions `openspec`

#### Scenario: A repeat
- **WHEN** `install` is run twice in a row
- **THEN** the second run changes no file and creates no backup

#### Scenario: Old schema copies
- **WHEN** `~/.local/bin/openspec-after-update.py` is equal to its last deployment
- **THEN** it is removed and named; an edited one is kept and named as `drift`

#### Scenario: A launchd job of the old version
- **WHEN** `~/Library/LaunchAgents/local.openspec-after-update.plist` exists
- **THEN** a line names the file for the user to remove; `install` does not touch it

### Requirement: Doctor without schema
`solo-sdd doctor` SHALL check and print one line `ok|warn|fail <what>: <detail>` each: Python 3.9+ for the current interpreter and for `/usr/bin/python3`; copies without `missing`, `drift` and `unreachable` (otherwise `fail`); the other checks by the requirement Doctor setup checks. It SHALL NOT check `openspec` or a schema. Exit code 1 if there is at least one `fail`, otherwise 0.

#### Scenario: No OpenSpec needed
- **WHEN** `openspec` is not installed, and everything else is in order
- **THEN** no line mentions `openspec`, exit code 0

#### Scenario: Python
- **WHEN** `solo-sdd doctor` is run
- **THEN** checked: Python 3.9+ for the current interpreter and for `/usr/bin/python3`

#### Scenario: Copies with a divergence
- **WHEN** there is a copy in the state `missing`, `drift` or `unreachable`
- **THEN** a `fail` line for the copies

### Requirement: Project init tree
`solo-sdd init [folder]` SHALL refuse with code 1 and `not a git repository: git init` in a folder without git. Otherwise it SHALL create the missing ones of `solo-sdd/project.md`, `solo-sdd/analyze.md`, `solo-sdd/specs/`, `solo-sdd/changes/`, `docs/waiting.md` from the package templates and `solo-sdd/config`, change no existing file, print one line per created path and last `next: /project-init`. A folder with `openspec/` and no `solo-sdd/` SHALL get no file, only the import hint.

#### Scenario: A new project
- **WHEN** `solo-sdd init` is run in an empty git repository with no `openspec` anywhere
- **THEN** the five paths and `solo-sdd/config` exist, `solo-sdd validate --all` ends with code 0

#### Scenario: A repeat
- **WHEN** `solo-sdd init` is run a second time in the same folder
- **THEN** no file is changed, there are no lines about created files

#### Scenario: Not a repository
- **WHEN** `solo-sdd init` is run in a folder without `.git`
- **THEN** exit code 1, the line `not a git repository: git init`, no file is created

#### Scenario: A project on openspec
- **WHEN** the folder has `openspec/` and no `solo-sdd/`
- **THEN** no file is created, a line names `solo-sdd import openspec`, exit code 0

### Requirement: Process guard connected
`solo-sdd install --hooks` SHALL connect `process-guard.py` as a PreToolUse hook on `Bash|Monitor` as the README names it, with deny rules for `pkill`, `killall`, `kill`, `osascript`, `launchctl`, `shutdown`, recording in `_hooks` only what it added and never duplicating an entry connected by hand. `uninstall` SHALL remove only the recorded entries. `doctor` SHALL print `ok process guard: connected` or `warn process guard: not connected`.

#### Scenario: Connected by hand
- **WHEN** `settings.json` already has the process-guard hook entry and `install --hooks` runs
- **THEN** there is one such entry, `_hooks` does not record it, `uninstall` keeps it

#### Scenario: A fresh home
- **WHEN** `install --hooks` runs on a home without settings and then `uninstall`
- **THEN** after install the hook and the six deny rules are there, after uninstall none of them

### Requirement: Doctor hook errors
When `_hooks` is in the state, `solo-sdd doctor` SHALL print `ok model policy` or `fail model policy: <reason>` when the deployed `~/.claude/hooks/model-policy.json` is missing or cannot be parsed. In any case it SHALL print `warn hook errors: <n> in the last 7 days, last: <line>` when `~/.claude/hook-state/errors.log` has lines dated within the last 7 days, and `ok hook errors: none` otherwise; a line without a leading ISO time is not counted.

#### Scenario: A broken policy
- **WHEN** hooks are connected and `~/.claude/hooks/model-policy.json` is truncated
- **THEN** `doctor` prints `fail model policy:` with the parse error and exits 1

#### Scenario: Recent errors
- **WHEN** `errors.log` has two lines of yesterday and one of a month ago
- **THEN** `doctor` prints `warn hook errors: 2 in the last 7 days, last:` with the later line of yesterday

#### Scenario: A clean log
- **WHEN** `errors.log` is missing or has only older lines
- **THEN** `doctor` prints `ok hook errors: none`

### Requirement: Purge keeps what solo-sdd did not write
`solo-sdd uninstall --purge` SHALL delete in `~/.local/share/solo-sdd/` only the entries solo-sdd writes there (the `targets.json` destinations under it, the state file, `backup/`, `checks/`), keep every other entry, name each kept top-level entry on a `kept` line, and delete the folder itself only when it is empty. An own-named entry that is a symbolic link is kept; an entry it cannot delete gets a `no access` line and exit code 1.

#### Scenario: Any foreign entry stays
- **WHEN** the data folder holds entries of any names other than the ones solo-sdd writes (a dotfile, `state.json.bak`, `templatesx`), and `uninstall --purge` is run
- **THEN** each of them is still there with its content, and a `kept` line names each top-level one

#### Scenario: The checks cache and backups go
- **WHEN** `checks/` and `backup/` exist in the data folder and `uninstall --purge` is run
- **THEN** both are deleted and no `kept` line names them

#### Scenario: An own name that is a link
- **WHEN** `checks` in the data folder is a symbolic link to a folder outside it, and `uninstall --purge` is run
- **THEN** the link and the outside folder's content stay, and a `kept` line names `~/.local/share/solo-sdd/checks`

#### Scenario: An entry that cannot be deleted
- **WHEN** an own entry of the data folder cannot be deleted for lack of permission
- **THEN** a `no access` line names it, the other entries are handled as usual, exit code 1
