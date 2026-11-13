# dispatch-eval Specification

## Purpose
Replaying a consumer project's archived changes with different dispatcher configurations and comparing the configurations by one method: oracle tests, time, cost.

## Requirements

### Requirement: Eval set file
A replay set SHALL be described by a JSON file with the fields from the scenario "Set fields"; the change base SHALL be the first parent of `oracle`. `sdd-eval.py setup` SHALL reject the set with code 2, creating nothing, if the condition of the scenario "Set rejection reasons" holds.

#### Scenario: Set fields
- **WHEN** the set file is read
- **THEN** `project` is the path to the project's main folder, `prepare` the copy prepare command (for example `npm ci`), the optional `oracle_prepare` a command in the oracle worktree after laying over the test files and before the tests (rebuild the `prepare` results that depend on the change code), `answers` an object question → answer, `changes` a list `{id, oracle}`: `id` is the change folder name in the archive without the date, `oracle` the commit in the main branch that merged the change

#### Scenario: The main branch
- **WHEN** `setup` checks `oracle`
- **THEN** the main branch is determined as in `spec-dispatch`: the project's `origin/HEAD`, otherwise the current one

#### Scenario: Set rejection reasons
- **WHEN** the set has fewer than 8 changes, or an `id` repeats, or a change folder is not in the archive, or `oracle` is not found in the main branch, or the oracle commit changes no test file (by the set's `tests` patterns, by default `*.test.*` and `tests/`)
- **THEN** `setup` rejects the set with code 2 and creates nothing

#### Scenario: An incomplete set
- **WHEN** the set has 7 changes or one has no `oracle`
- **THEN** `setup` ends with code 2 and names the change and the field; there are no copy folders

#### Scenario: An oracle without tests
- **WHEN** a change's oracle commit changes only code and documents
- **THEN** `setup` ends with code 2 with the line `oracle without tests: <id>`

### Requirement: Replay copy per change
`sdd-eval.py setup <set> --config <file> --out <folder>` SHALL create a separate project copy for every change: a `git clone` of the main folder on the change base, without a remote and tags, in `<folder>/<id>`, carry over the project documents and the change state before code, then run `prepare`. An existing copy folder gives code 2. Two `setup` runs with one set and configuration SHALL give the same `HEAD` and tree hash of `solo-sdd/` in every copy.

#### Scenario: What goes into a copy
- **WHEN** `setup` created a change copy
- **THEN** it got: `CLAUDE.md` and the top-level files of `solo-sdd/` (`project.md` and others); the main folder's `AGENTS.md`, where the "Delivery" section lines are replaced with "Mode: local", the "Working copy" section with the configuration lines, and `Orchestrators:` with 1; the main folder's `solo-sdd/specs` without the requirements this change added (`ADDED`), and a capability without remaining requirements is deleted; the folders of the direct dependencies from the change's `Depends On` in `solo-sdd/changes/archive/` (other archived changes do not get into the copy); the change folder from the archive in `solo-sdd/changes/<id>` in the state before code (all tasks unchecked, in `verification.md` the sections `Result`, `Not Verified` and `Decisions Without Owner` empty, no `CLAIM` and `WAITING`); other git-ignored documents of the main folder (`docs/*`)

#### Scenario: The copy mark and the output
- **WHEN** the copy is prepared
- **THEN** `<folder>/<id>/.sdd-eval` (JSON, excluded from git through `info/exclude`) records the configuration name, `id`, `oracle`, `project`, the `spec after the change` lines, `answers` and `oracle_prepare`: `run`, `metrics` and `compare` read them; `setup` prints the line `<id> <HEAD> <solo-sdd hash>`

#### Scenario: A repeated setup
- **WHEN** `setup` runs twice on one set and configuration into different folders
- **THEN** copies of the same name have the same `git rev-parse HEAD` and tree hash of `solo-sdd/`

#### Scenario: The delta changes an existing requirement
- **WHEN** the change delta has `MODIFIED`, `REMOVED` or `RENAMED`
- **THEN** the spec in the copy stays as in the main folder, `setup` prints the line `spec after the change: <id> <requirement>`, and the same line gets into the `compare` report

#### Scenario: The preparation failed
- **WHEN** `prepare` in a copy ended with non-zero
- **THEN** `setup` names the change and the last output lines and ends with code 3, the other copies stay

### Requirement: Replay run
`sdd-eval.py run <folder> --label <label>` SHALL run `claude -p "/spec-dispatch"` in every copy of `<folder>` with the dispatcher model from `--dispatcher-model` (default `sonnet`), at most `--parallel` copies at once (default 1), and append the copy's entry to `<folder>/runs/<label>.json`. A copy whose run ended with non-zero or without a merged change `run` SHALL mark `not finished` and not repeat. An existing log with this label gives code 2, no runs.

#### Scenario: The copy entry
- **WHEN** a copy's run finished
- **THEN** the log after it has the session id (set in advance through `--session-id`), the configuration from `.sdd-eval`, the start and end time, the exit code and the result; the change is merged if the copy's main branch moved ahead of the base and the change folder is in the copy's `solo-sdd/changes/archive/`

#### Scenario: One change failed
- **WHEN** in one of the copies the dispatcher ended with an error
- **THEN** the copy has `not finished` in the run log, the other copies are launched and finished

### Requirement: Metrics by one method
`sdd-eval.py metrics <folder> --label <label>` SHALL compute from the Claude Code logs of the run's sessions and all their subagents, for every copy and in total, tokens, cost, time, the number of subagents and returns, counting every API call once by the message id. The result SHALL be written to `<folder>/runs/<label>.metrics.json`; the counting method SHALL be described in `tests/eval/README.md`.

#### Scenario: Metrics content
- **WHEN** `metrics` counts a copy
- **THEN** the result holds: input (with cache) and output for every pair of role and model (one message is written as several lines, the maximum of each counter is taken); the session output by model from the `cost-state` record if there is one, because the log lines keep incomplete output; the cost by `tests/eval/prices.json` (`--prices`), a model without a price is `null` with its name, not zero; the time from the first orchestrator launch to the commit into the copy's main branch; the number of subagents by role (`orchestrator`, `implement`, `general`, `review`) and the dispatcher session tokens as a separate role `dispatcher`; the number of returns to an orchestrator (the dispatcher's SendMessage calls: by `spec-dispatch` it sends them only after a status) and refused status handbacks

#### Scenario: One session
- **WHEN** `metrics --session <id>` is called
- **THEN** the same is computed for one session of a whole run, plus the number of merged changes (PR, `land-local`, `git merge`) and the time from the first orchestrator launch to the last merge (to check against past analyses); the log is looked up in all folders of `~/.claude/projects`: the folder depends on the earlier project path

#### Scenario: A repeated line in the log
- **WHEN** the same API call is written in the log twice (a resumed session) or a message is split into several lines
- **THEN** its tokens count in the sum once

#### Scenario: No log
- **WHEN** the copy's session log is in no folder of `~/.claude/projects`
- **THEN** the copy has `journal not found` in the metrics, not zeros; exit code 3 after counting the rest

### Requirement: Oracle tests and comparison
`sdd-eval.py compare <folder> --a <label>... --b <label>...` SHALL for every copy of every run lay the oracle commit's test files over the result in a temporary worktree and run the test command from the copy's `AGENTS.md`. A change SHALL count as done if it is merged into the copy's main branch and the oracle tests passed; a test that cannot find the needed module or export SHALL count as failed, not skipped. If a configuration has fewer than two runs, `compare` SHALL end with code 2.

#### Scenario: Where runs are looked up
- **WHEN** a run label is named
- **THEN** the log is looked up in `<folder>/runs/` and in `<folder>/*/runs/`: the second run goes on new copies in a neighbouring folder; every label counts once, however many times it is named, and a configuration's runs are counted by different labels

#### Scenario: The result to lay over
- **WHEN** `compare` lays over the oracle tests
- **THEN** the result is the last commit of the copy's main branch, the test files come from the change's oracle commit; the worktree is prepared by `sdd-worktree.py setup` and gets links to the ignored `prepare` results of the copy; the test command is the first backquoted value of the `Tests` row of the `AGENTS.md` section "Commands" of the copy, with the test file paths appended

#### Scenario: An oracle_prepare failure
- **WHEN** `oracle_prepare` ended with non-zero or by the deadline
- **THEN** the tests do not run, the change is not done in this run, the line `oracle_prepare: code <N>` or `oracle_prepare: timeout <N> s` is among the failures

#### Scenario: No test command
- **WHEN** there is no command, the command is a chain (`&&`, `||`, `;`, `|`: the files would reach only the last link) or `git` fails on the copy
- **THEN** code 3 with the copy name, no report, this is not a change failure

#### Scenario: Report content
- **WHEN** `compare` finished successfully
- **THEN** the report holds: a table by change (done in each run, time, cost), totals by configuration (cost `n/a` if a copy has none), the list of flipped changes (done in all runs of one configuration and not done in at least one run of another) with the names of the failed oracle tests, and the `spec after the change` lines

#### Scenario: Merged, oracle red
- **WHEN** a change is merged in a run, and the oracle tests fail on the result
- **THEN** the table shows `merged, oracle red` for the change with the names of the failed tests, it does not count as done

#### Scenario: One run per configuration
- **WHEN** one label is passed for `--b`
- **THEN** `compare` ends with code 2 and the line `2 or more runs needed: b`

### Requirement: Owner questions in replay
`setup` SHALL copy into the copy the archive folder of every change from `Depends On` of the replayed change. `run` SHALL pass the dispatcher the answers of the set's `answers` field (question → answer) and a ban on asking the owner through `--append-system-prompt`; the prompt stays `/spec-dispatch`. An `AskUserQuestion` call or a "Needs from you" line from the dispatcher SHALL give the copy the mark `question: <text>`. `compare` SHALL list such changes "With a question", not as flipped.

#### Scenario: The mark text
- **WHEN** `AskUserQuestion` was called in the log of the copy or its subagents, or the dispatcher wrote a "Needs from you" line
- **THEN** the text is the call's questions (without them `no text`) or the rest of the line, and if it is empty, the next non-empty line of the message; no mark comes from the whole value `none` or a value starting with the word `nothing`: that is a field of the dispatcher's final report

#### Scenario: A dependency in the archive
- **WHEN** change `b` from the set has the archived change `a` in `Depends On`
- **THEN** copy `b` has `solo-sdd/changes/archive/<date>-a/`, the dispatcher's plan does not print the line "unknown dependency"

#### Scenario: The dependency is not in the archive
- **WHEN** `Depends On` of change `b` holds a name that is not in the project archive (`none` and other empty values are parsed as in `sdd-dispatch-plan.py`)
- **THEN** `setup` prints the line `dependency not archived: b <name>` and still creates the copy; the dispatcher's question about it gives the copy the mark `question`

#### Scenario: The dispatcher asked anyway
- **WHEN** the Claude Code log of copy `b` has an `AskUserQuestion` call or a dispatcher message with a "Needs from you" line (in `claude -p` there is no question window, requirement Owner questions of `spec-dispatch`)
- **THEN** the copy has `question: <text>` in the run log, `compare` lists `b` "With a question", not among the flipped ones

#### Scenario: A question in one run
- **WHEN** change `b` has a copy with the mark `question` only in run `b-1`
- **THEN** in the `compare` table `b` in `b-1` has `question` next to the outcome; whether it is done is decided by merge and the oracle tests, as without a question; `b` is in the "With a question" list and not in the flipped list
