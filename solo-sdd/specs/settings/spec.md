# settings Specification

## Purpose
Keeps every project setting of solo-sdd in one file with known keys and defaults per mode, and lets the user read and change them with one command.

## Requirements

### Requirement: Settings file
Project settings SHALL live in `solo-sdd/config`, one `key: value` per line, `#` starting a comment, list values separated by commas. A missing file SHALL mean all defaults. A line that is not `key: value` or names an unknown key SHALL make the `config` command and the scripts fail with the file, the line number and the reason; the hooks SHALL use the defaults and log it (fail-open).

#### Scenario: A list value
- **WHEN** a registered key takes a list and the file has it as `staging, main`
- **THEN** `solo-sdd config get` of that key prints `staging, main`

#### Scenario: A broken file in a hook
- **WHEN** the file has a broken line and the `stop` hook runs
- **THEN** the hook uses the defaults and writes the reason to `~/.claude/hook-state/errors.log`

#### Scenario: A broken line
- **WHEN** line 4 is `delivery.mode pr` without a colon
- **THEN** `solo-sdd config list` exits 1 and names `solo-sdd/config:4`

### Requirement: Defaults by mode
Every registered key SHALL have a type, its allowed values and a default; a key MAY have a different default for `mode: team`. The value in effect SHALL be the file value, else the key's old source: for `delivery.mode` and `delivery.merge` the first allowed `Mode:` or `Merge:` item of the `## Delivery` section of `AGENTS.md`, for another key the item its requirement names, source named after that file; else the mode default, else the built-in default.

#### Scenario: Team default
- **WHEN** the file has only `mode: team`, `AGENTS.md` has no `## Delivery` item, and `delivery.mode` defaults to `local` and to `pr` for a team
- **THEN** `config get delivery.mode` prints `pr`

#### Scenario: File wins
- **WHEN** the file has `mode: team` and `delivery.mode: local`
- **THEN** `config get delivery.mode` prints `local`

#### Scenario: Delivery section kept
- **WHEN** there is no `solo-sdd/config`, and `AGENTS.md` has `## Delivery` with `- Mode: pr` and `- Merge: cloud`
- **THEN** `config list` prints `delivery.mode pr AGENTS.md` and `delivery.merge squash default`

### Requirement: Config command
`solo-sdd config list` SHALL print every key, its value in effect and its source (`file`, `AGENTS.md`, `mode`, `default`). `get <key>` SHALL print the value on stdout and `source: <source>` on stderr. `set <key> <value>` and `unset <key>` SHALL change only that line and keep comments and order. A wrong key or value SHALL be refused with exit 1 and the allowed keys or values.

#### Scenario: Set keeps the rest
- **WHEN** the file has a comment line and two keys, and `config set dispatch.limit 3` runs
- **THEN** only the `dispatch.limit` line changes; the comment and the other key keep their bytes

#### Scenario: A wrong value
- **WHEN** `config set delivery.mode cloud` runs
- **THEN** exit 1, the message lists `local, pr`, the file is unchanged

#### Scenario: Get names the source
- **WHEN** there is no `solo-sdd/config`, and `AGENTS.md` has `## Delivery` with `- Mode: pr`
- **THEN** `config get delivery.mode` prints `pr` on stdout and `source: AGENTS.md` on stderr

### Requirement: Readers use the settings
The dispatch plan, `spec-dispatch`, `ship`, `spec-next` and the `stop` hook SHALL read the delivery mode and merge method, the orchestrator limit, the review rounds and the reply language from the settings. Without the key in the file they SHALL keep the old source (`## Delivery` of `AGENTS.md`, `SOLO_SDD_REPLY_LANG`) before the default.

#### Scenario: Limit from config
- **WHEN** `solo-sdd/config` has `dispatch.limit: 3` and `AGENTS.md` says `Orchestrators: 2`
- **THEN** the dispatch plan prints `limit: 3`

#### Scenario: Old source kept
- **WHEN** there is no `solo-sdd/config`, and `AGENTS.md` has `- Mode: pr`
- **THEN** the dispatch plan uses `pr`

### Requirement: Key descriptions
Every key of the settings registry and every pattern key SHALL have a group and a one-sentence description in the package. A key without them SHALL fail the test suite.

#### Scenario: A new key without a description
- **WHEN** a key is added to the registry without a description
- **THEN** the settings test fails and names the key

#### Scenario: A new pattern key without a description
- **WHEN** a pattern key is added without a group
- **THEN** the settings test fails and names the pattern

### Requirement: Describe a setting
`solo-sdd config describe [<key>]` SHALL print for each registered key, then each pattern and each pattern key set in the file, or for the one named, its group, description, type with allowed values, default, team default, value in effect and source; `config list --json` the same fields as a list of objects, plain `config list` unchanged. An unknown key, or a broken file as `config list` refuses it, SHALL give exit 1.

#### Scenario: One key
- **WHEN** `solo-sdd config describe delivery.mode` runs with no `solo-sdd/config` and no `## Delivery` in `AGENTS.md`
- **THEN** the output names the group `delivery`, its description, `local, pr`, default `local`, team default `pr`, value `local`, source `default`

#### Scenario: JSON list
- **WHEN** `solo-sdd config list --json` runs
- **THEN** a list with one object per registered key, each with `key`, `group`, `about`, `type`, `allowed`, `default`, `team_default`, `value` and `source`

#### Scenario: Unknown key
- **WHEN** `solo-sdd config describe delivery.color` runs
- **THEN** exit 1, the message lists the known keys

#### Scenario: Pattern keys
- **WHEN** the file has `checklist.money.paths: billing/**` and `config describe` runs
- **THEN** after the registered keys come `checklist.<name>.paths` and `checklist.<name>.file` with their descriptions, then `checklist.money.paths` with value `billing/**` and source `file`

#### Scenario: A broken file
- **WHEN** line 4 of `solo-sdd/config` is `delivery.mode pr` without a colon
- **THEN** `config describe` exits 1 and names `solo-sdd/config:4`, as `config list` does

### Requirement: Text settings
A registry key of kind `text` SHALL take one line of printable characters, at most 200, with the ends trimmed; a line break, a control character or a longer value SHALL be refused with exit 1 and the reason, the file unchanged. `config describe` SHALL name the kind as `text: one line, at most 200 characters`; `solo-sdd settings` SHALL edit it as a one-line input that Esc leaves unchanged.

#### Scenario: A title rule with spaces
- **WHEN** `solo-sdd config set delivery.pr-title "<id>: <summary>"` runs
- **THEN** `config get delivery.pr-title` prints `<id>: <summary>` with `source: file`

#### Scenario: A too long value
- **WHEN** `config set delivery.deploy` gets 201 characters
- **THEN** exit 1 names `at most 200 characters`, the file is unchanged

### Requirement: Delivery items in config
The keys `delivery.pr-title` (default `the change name`), `delivery.deploy` (default `no`) and `delivery.owner-only` (paths, default empty) SHALL take, without a file value, the text after the "PR title:" and "Deploy:" labels of the "Delivery" section of `AGENTS.md`, trimmed and as is, and the backquoted patterns of every "Owner only:" item there, source `AGENTS.md`. `ship`, `spec-dispatch` and `project-init` SHALL read the three through `solo-sdd config get`.

#### Scenario: The old item
- **WHEN** there is no `solo-sdd/config`, and "Delivery" has "Owner only: `global/work_hooks.py`, `docs/**`"
- **THEN** `config get delivery.owner-only` prints `global/work_hooks.py, docs/**` with `source: AGENTS.md`

#### Scenario: The file wins
- **WHEN** the file has `delivery.deploy: on merge into main, Cloudflare Pages` and "Delivery" has "Deploy: no"
- **THEN** `config get delivery.deploy` prints the file value with `source: file`

#### Scenario: A long old item
- **WHEN** there is no file value, and "Delivery" has a "Deploy:" item of 240 characters with backquotes
- **THEN** `config get delivery.deploy` prints the 240 characters as written with `source: AGENTS.md`: the 200-character limit holds for a value set in the file

### Requirement: CI wait settings
`sdd-pr.py wait` and `ship` SHALL take the whole time limit from `delivery.ci-timeout` (default 1200 s), the stuck check limit from `delivery.ci-stuck` (300 s) and the no-checks limit from `delivery.ci-no-checks` (180 s). A `--timeout` or `--stuck` flag of `wait` SHALL win over the setting; while one of the three keys is set, a line on stderr before the CI line SHALL name each limit with its source, stdout unchanged.

#### Scenario: A slow CI
- **WHEN** the file has `delivery.ci-timeout: 3600`, and `sdd-pr.py wait <url>` runs without `--timeout`
- **THEN** stderr names `timeout 3600 s (file)`, and the wait gives up only after 3600 s

#### Scenario: The flag wins
- **WHEN** the file has `delivery.ci-timeout: 3600`, and `wait <url> --timeout 60` runs
- **THEN** stderr names `timeout 60 s (flag)`

#### Scenario: The defaults
- **WHEN** none of the three keys is set, and `wait <url> --timeout 60` runs
- **THEN** stderr has no limits line

#### Scenario: A stuck limit above the timeout
- **WHEN** the file has `delivery.ci-stuck: 900` and `delivery.ci-timeout: 600`, and a required check never starts
- **THEN** `wait` gives `CI: infra` after 600 s: no limit extends the whole wait

### Requirement: Merge gate settings
With `delivery.require-ci: off` a PR whose checks stay empty past `delivery.ci-no-checks`, while the base branch requires no check, SHALL give `CI: none`, code 0 from `wait` and `ship`, and be merged by `merge` and `land`; a red, pending, stuck or missing required check SHALL still block. `delivery.code-scanning: warn` SHALL print the open alerts and merge, `off` SHALL not request them; `gate` (default) keeps code 8.

#### Scenario: A project without CI
- **WHEN** `delivery.require-ci` is `off` and the PR has no checks
- **THEN** `wait` prints `CI: none` with code 0, `merge` merges with code 0

#### Scenario: A red check with CI optional
- **WHEN** `delivery.require-ci` is `off` and one check is red
- **THEN** `wait` prints `CI: red`, `merge` refuses with code 1

#### Scenario: CI optional with unread branch rules
- **WHEN** `delivery.require-ci` is `off`, the PR has no checks, and the branch rules request failed
- **THEN** `wait` gives `CI: infra` "no checks", `merge` refuses with code 1: unread rules may hold a required check

#### Scenario: Scanning alerts as a warning
- **WHEN** `delivery.code-scanning` is `warn` and the PR has one open alert
- **THEN** `wait` prints `CI: green` and the alert line with code 0, and the PR is merged

### Requirement: PR shape settings
`delivery.delete-branch: off` SHALL keep the remote and the local branch after a PR merge by `merge` and `land`; `land-local` always deletes. `delivery.draft: on` SHALL make `sdd-pr.py open` and `ship` create a draft, and `merge`/`land` mark a draft PR ready for review after every gate, right before the merge request; a code 8 gate leaves it a draft, a failed ready request SHALL give code 1 without a merge.

#### Scenario: Keep the branch
- **WHEN** `delivery.delete-branch` is `off` and `land` merges `change/a`
- **THEN** the remote and the local `change/a` exist after the merge

#### Scenario: A draft PR
- **WHEN** `delivery.draft` is `on` and `sdd-pr.py open` runs
- **THEN** the fake `gh` log has `pr create --draft`, and `merge` later calls `pr ready` before the merge request

#### Scenario: A failed ready request
- **WHEN** `delivery.draft` is `on`, the checks passed, and `gh pr ready` fails
- **THEN** code 1 naming the ready step, no merge request, the PR stays a draft

### Requirement: Delivery settings from the main folder
`sdd-pr.py` SHALL read the keys of CI wait settings, Merge gate settings and PR shape settings from the main folder's `solo-sdd/config`, never from the PR or the WORKTREE; broken settings SHALL exit 1 before any merge request. Who may change them is the owner, by Owner-only paths gate of `pr-tool`: a PR that edits `solo-sdd/config` waits for the owner.

#### Scenario: A PR switches CI off for itself
- **WHEN** the WORKTREE `solo-sdd/config` has `delivery.require-ci: off`, the main folder's has none, and the PR has no checks
- **THEN** `wait` gives `CI: infra` "no checks", `merge` refuses with code 1

### Requirement: Local merge method
The key `delivery.local-merge` (`merge`, `squash`, `rebase`; default `merge`) SHALL choose how `sdd-dispatch.py land-local` merges the change branch; `delivery.merge` SHALL describe only pull requests. `config describe delivery.merge` SHALL name `delivery.local-merge` for local delivery.

#### Scenario: The default keeps today
- **WHEN** the file has no `delivery.local-merge`
- **THEN** `config get delivery.local-merge` prints `merge` with `source: default`
