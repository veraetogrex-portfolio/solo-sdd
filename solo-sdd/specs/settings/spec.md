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
`solo-sdd config list` SHALL print every key, its value in effect and its source (`file`, `AGENTS.md`, `project.md`, `mode`, `default`). `get <key>` SHALL print the value on stdout and `source: <source>` on stderr. `set <key> <value>` and `unset <key>` SHALL change only that line and keep comments and order. A wrong key or value SHALL be refused with exit 1 and the allowed keys or values.

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

### Requirement: Subagent model settings
`agents.orchestrator-model` (default `opus`), `agents.review-model` (empty: the session's main model), `agents.lookup-model` and `agents.test-model` (`haiku`, the latter for paid product calls in tests) SHALL take one model name, `agents.dispatcher-effort` one of `low`, `medium`, `high` (default `low`). `spec-dispatch`, `spec-next`, `spec-audit` and the global rules SHALL read them; `opus`, `Opus` and `/effort low` in other requirements name these defaults.

#### Scenario: Another orchestrator model
- **WHEN** the file has `agents.orchestrator-model: fable`
- **THEN** the laid-out `spec-dispatch` text tells the dispatcher to read `agents.orchestrator-model` and launch each orchestrator with that model, `opus` when it is not set

#### Scenario: A model name with a space
- **WHEN** `config set agents.lookup-model "haiku 4"` runs
- **THEN** exit 1 names one model name of ASCII letters, digits, `.`, `-`, `_`, `[` and `]`, the file is unchanged

#### Scenario: The defaults
- **WHEN** the file has none of the six keys
- **THEN** `config list` prints `agents.orchestrator-model opus default` and `agents.dispatcher-effort low default`

### Requirement: Executor setting from the owner
`agents.executor` (`self`, `codex`; default `self`): `codex` SHALL count as the owner naming `codex-orchestration`. The global rules SHALL let an agent set or unset `agents.executor` only on the owner's words in the chat.

#### Scenario: Codex as the executor
- **WHEN** the file has `agents.executor: codex`, and the owner asks `spec-next` to take a change without naming Codex
- **THEN** Codex executors write the code by `codex-orchestration`, the lead agent accepts the result with its own commands

### Requirement: Project models within the machine policy
When the event folder's `solo-sdd/config` sets `agents.orchestrator-model`, `agents.review-model` or `agents.lookup-model`, the guard hook SHALL refuse a launch of that role on that model while the model is outside the role's machine list (`main` for orchestrator and review, `cheap` for lookup), naming the key and the list. `SOLO_SDD_EXPENSIVE_OK=1` lifts it; a broken config SHALL keep the role rules alone and write `errors.log`. `agents.test-model` SHALL stay bound by Test model allowlist.

#### Scenario: A project widens the lookup model
- **WHEN** the file has `agents.lookup-model: sonnet`, and a `Lookup:` subagent of type `Explore` starts on `sonnet`
- **THEN** the hook denies it, and the reason names `agents.lookup-model` and the `cheap` list

#### Scenario: A cheaper orchestrator
- **WHEN** the file has `agents.orchestrator-model: sonnet`, and the main session launches `Orchestrator a` on `sonnet`
- **THEN** the hook denies it, and the reason names `agents.orchestrator-model` and the `main` list

#### Scenario: A project narrows the review model
- **WHEN** the file has `agents.review-model: fable`, `fable` is in `main`, and a `Review:` subagent starts on `fable`
- **THEN** the hook allows it

#### Scenario: A broken config
- **WHEN** the file has a broken line, and the main session launches `Orchestrator a` on `sonnet`
- **THEN** the hook allows it by the role rules, and the temporary home's `errors.log` names the line

### Requirement: Branch and commit prefixes
The change branch SHALL be `<delivery.branch-prefix><id>` (default `change/`), the plan branch `<delivery.plan-prefix><first id>` (default `plan/`), and a light commit subject SHALL start with `commit.light-prefix` (text, default `light:`), matched as plain text. The dispatch scripts, `sdd-pr.py`, `sdd-eval.py`, `spec-dispatch`, `spec-plan`, `work-status`, `report` and the global rules SHALL take them; `change/<id>`, `plan/<first id>` and `light:` in other requirements name these defaults.

#### Scenario: A team prefix
- **WHEN** the file has `delivery.branch-prefix: feat/`, open changes `a` and `b` are ready, and the repository has branches `change/a` and `feat/b`
- **THEN** `sdd-dispatch-plan.py` prints `launch: a`, and `b` waits with `not merged: branch feat/b`

#### Scenario: Defaults keep the names
- **WHEN** the file has none of the three keys, and the repository has branch `change/a`
- **THEN** `a` waits with `not merged: branch change/a`, and `work-status` counts commits whose subject starts with `light:`

#### Scenario: A light prefix with pattern characters
- **WHEN** the file has `commit.light-prefix: [quick]`, and the log has `[quick] fix typo` and `q fix`
- **THEN** `work-status` counts one light commit

### Requirement: Prefix change guard
`config set` and `config unset` of `delivery.branch-prefix`, and the settings screen, SHALL refuse a value other than the one in effect, while a local branch `<prefix in effect><id>` of an open change exists, with exit 1, the branch names and the file unchanged. A prefix for which `<prefix>a` is not a valid git branch name, and equal branch and plan prefixes, SHALL be refused. Outside a git repository the branch check passes; a failed branch listing SHALL refuse with git's message.

#### Scenario: A leftover change branch
- **WHEN** the repository has branch `change/a`, `a` is an open change, and `config set delivery.branch-prefix feat/` runs
- **THEN** exit 1 names `change/a`, `config get delivery.branch-prefix` still prints `change/`

#### Scenario: A branch of an archived change
- **WHEN** the repository has branch `change/old`, `old` is archived, and `config set delivery.branch-prefix feat/` runs
- **THEN** code 0, `config get delivery.branch-prefix` prints `feat/`

#### Scenario: Equal prefixes
- **WHEN** `config set delivery.plan-prefix change/` runs while `delivery.branch-prefix` is `change/`
- **THEN** exit 1 names `delivery.branch-prefix`, the file is unchanged

#### Scenario: A prefix git refuses
- **WHEN** `config set delivery.branch-prefix "feat/*"` runs
- **THEN** exit 1 names a valid branch name, the file is unchanged

### Requirement: Change size limits
`solo-sdd validate` SHALL refuse more tasks in `tasks.md` than `process.max-tasks` (default 10) and a requirement longer than `process.requirement-max-chars` (default 500), naming the limit and its source. `spec-plan` and `spec-analyze` SHALL take these and `process.bugfix-max-tasks` (default 5) through `solo-sdd config get`; a bug fix takes the smaller task limit. `config set` SHALL refuse a task limit below 3 and a length below 100. 10, 5 and 500 in other requirements name these defaults.

#### Scenario: A project with larger units
- **WHEN** the file has `process.max-tasks: 14`, and a change has 12 tasks
- **THEN** `solo-sdd validate <id>` passes it

#### Scenario: The default limit
- **WHEN** the file has no `process.max-tasks`, and a change has 11 tasks
- **THEN** `validate` fails with `too many tasks: 11 > 10 (default)`

#### Scenario: A file limit on length
- **WHEN** the file has `process.requirement-max-chars: 300`, and a requirement text has 400 characters
- **THEN** `validate` fails naming `400 > 300 (file)`

#### Scenario: A limit no change can meet
- **WHEN** `config set process.max-tasks 2` runs
- **THEN** exit 1 names `3`: the `Acceptance` group alone holds two tasks; the file is unchanged

### Requirement: Process cadence settings
`spec-next` SHALL propose `spec-audit` when the archive count after its archive is a multiple of `process.audit-every` (default 5). With `process.analyze: off` `spec-plan` and `spec-next` SHALL skip the `spec-analyze` pass, and their report SHALL hold `Analyze: off (solo-sdd/config)`. `spec-plan`, `spec-next` and `ALGORITHM.md` SHALL let an agent change the five keys only on the owner's words in the chat.

#### Scenario: Analyze switched off
- **WHEN** the file has `process.analyze: off`
- **THEN** the laid-out `spec-next` text skips the analyze gate for this setting and names the report line `Analyze: off (solo-sdd/config)`

#### Scenario: Audit every three archives
- **WHEN** the file has `process.audit-every: 3`
- **THEN** the laid-out `spec-next` text reads `process.audit-every` and names `Time for: /spec-audit on the main specs` at a multiple of it

### Requirement: Ignore list setting
The key `git.ignore` (paths, default `.claude/worktrees/, .env, .env.*, !.env.example`) SHALL list what the project keeps out of git; an item starting with `!` re-includes the path after it, as in `.gitignore`. `config set git.ignore`, `config unset git.ignore` and the settings screen SHALL print `run: solo-sdd ignore --write`.

#### Scenario: Keep the archive private
- **WHEN** `config set git.ignore ".claude/worktrees/, .env, solo-sdd/changes/archive/"` runs
- **THEN** code 0 and the hint line `run: solo-sdd ignore --write`

#### Scenario: The example file stays in git
- **WHEN** the project has `.env.example`, `git.ignore` has its default, and `solo-sdd ignore --write` runs
- **THEN** `git check-ignore -q .env.example` exits 1 and `git check-ignore -q .env.local` exits 0

### Requirement: Process paths stay tracked
A `git.ignore` value SHALL be refused with exit 1 and the file unchanged (by `config set`, the settings screen, and as a broken line when the file is read) when one of its items, by git's matching, hides `AGENTS.md`, `CLAUDE.md`, `solo-sdd/` or a path under it other than `solo-sdd/changes/archive/`, or starts with `#`; the message names the item and the path it hides.

#### Scenario: Hiding the specs
- **WHEN** `config set git.ignore solo-sdd/` runs
- **THEN** exit 1 names `solo-sdd/`, the file is unchanged

#### Scenario: A glob that hides the rules
- **WHEN** `config set git.ignore "*.md"` runs
- **THEN** exit 1 names `*.md` and `AGENTS.md`, the file is unchanged

### Requirement: Ignore command
`solo-sdd ignore` SHALL print each `!` item of `git.ignore` and each other item no rule of the repository's `.gitignore` files outside its block hides (not `.git/info/exclude` or global excludes); `--write` SHALL put them between `# solo-sdd:begin` and `# solo-sdd:end` of the root `.gitignore` (no file or block: created; an empty list removes the block), other bytes kept. A tracked path of a hiding item SHALL be named with a shell-quoted `git rm --cached -r -- <path>` and stay tracked.

#### Scenario: A repeated write
- **WHEN** `solo-sdd ignore --write` runs twice
- **THEN** the second run prints `no change`, and every listed line occurs once

#### Scenario: A rule already hides it
- **WHEN** `.gitignore` has `.claude/` outside the block
- **THEN** the block has no `.claude/worktrees/` line

#### Scenario: A global rule does not count
- **WHEN** the global excludes file hides `.env` and the project's `.gitignore` does not
- **THEN** after `solo-sdd ignore --write` the block has `.env`

#### Scenario: A tracked file becomes ignored
- **WHEN** `git.ignore` names `docs/waiting.md` and git tracks it
- **THEN** the output names `git rm --cached -r -- docs/waiting.md`, `git ls-files docs/waiting.md` still lists it

### Requirement: Ignore command refusals
`solo-sdd ignore` SHALL exit 1 with every file unchanged when `.gitignore` has a begin marker without its end, an end marker without a begin, or two blocks (naming `.gitignore:<line>`), and outside a git repository (naming `not a git repository`). Without `solo-sdd/config` it SHALL use the defaults.

#### Scenario: An unclosed block
- **WHEN** line 3 of `.gitignore` is `# solo-sdd:begin` and no `# solo-sdd:end` follows
- **THEN** `solo-sdd ignore --write` exits 1 naming `.gitignore:3`, and `.gitignore` keeps its bytes

### Requirement: Project rules in config
`project.stage` (`demo`, `prod`; empty: decided by the task), `artifacts.language` (2 or 3 lowercase ASCII letters; `en`), `lessons.write` (`on`, `off`; `on`) and `lessons.max-lines` (20) SHALL be read by the global rules, `project-init` and `spec-plan`; 20 lines in other requirements name the last default. `spec-plan` SHALL write the artifacts' prose in `artifacts.language`. The global rules SHALL let an agent change the four keys only on the owner's words.

#### Scenario: A bad language code
- **WHEN** `config set artifacts.language "Russian language"` runs
- **THEN** exit 1 names 2 or 3 lowercase letters, the file is unchanged

#### Scenario: Artifacts in Russian
- **WHEN** the file has `artifacts.language: ru`
- **THEN** the laid-out `spec-plan` text writes the prose of the artifacts in that language, and keeps their headings, `SHALL`, `WHEN`, `THEN`, keys and paths in English, as `validate` reads them

#### Scenario: Lessons switched off
- **WHEN** the file has `lessons.write: off`
- **THEN** the laid-out global rules send a lesson to the report as `Lesson (not written): <sentence>` for this setting

### Requirement: Project lines as the old source
Without a file value `project.stage` and `artifacts.language` SHALL take the `Mode:` and `Language:` lines of `solo-sdd/project.md`, a final dot dropped, source `project.md`; a line value outside the allowed ones SHALL be left out, and `config get`, `list` and `describe` SHALL name it on stderr. A file value SHALL win over the line, and the global rules SHALL say so; `config set` SHALL leave `project.md` unchanged.

#### Scenario: The old line
- **WHEN** there is no file value and `solo-sdd/project.md` has `Mode: demo`
- **THEN** `config get project.stage` prints `demo` with `source: project.md`

#### Scenario: The file wins
- **WHEN** `solo-sdd/project.md` has `Mode: demo`, and `config set project.stage prod` runs
- **THEN** `config get project.stage` prints `prod` with `source: file`, `project.md` keeps its bytes

#### Scenario: A line value outside the list
- **WHEN** there is no file value and `solo-sdd/project.md` has `Mode: staging`
- **THEN** `config get project.stage` prints an empty line with `source: default`, and stderr names `Mode: staging`
