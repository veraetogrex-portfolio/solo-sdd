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
- **THEN** the result holds: input (with cache) and output for every pair of role and model (one message is written as several lines, the maximum of each counter is taken); the session output by model from the `cost-state` record if there is one, because the log lines keep incomplete output; the cost by `tests/eval/prices.json` (`--prices`), a model without a price is `null` with its name, not zero; the time from the first orchestrator launch to the commit into the copy's main branch; the number of subagents by role (`orchestrator`, `implement`, `general`, `review`, `lookup`, `analyze`, `attack`, `judge`, `check`) and the dispatcher session tokens as a separate role `dispatcher`; the number of returns to an orchestrator (the dispatcher's SendMessage calls: by `spec-dispatch` it sends them only after a status) and refused status handbacks

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
- **THEN** the report holds: a table by change (done with its path mark in each run, time, cost), totals by configuration (cost `n/a` if a copy has none), the list of flipped changes (done in all runs of one configuration and not done in at least one run of another) with the names of the failed oracle tests, the `Path:` list, and the `spec after the change` lines

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

### Requirement: Process path signals
`sdd-eval.py metrics <folder> --label <label>` SHALL add per copy `review_after_last_edit`, `review_rounds`, `important`, `live_in_scenario` and `analyze_findings`, all five and `important_sources` `null` when no orchestrator of the copy's session handed back `STATUS: archived`. A missing orchestrator journal SHALL not change the exit code. A subagent's final message SHALL be the `message` of its last `SubagentHandback` call, else its last assistant text.

#### Scenario: An honest path
- **WHEN** the fixture orchestrator edited code, ran `Review: a` (one `Important`), edited code, ran `Review: b` (no `Important`), edited `tasks.md`, wrote `Analyze: 6 findings, kept 2, dropped 4; CRITICAL 0 · HIGH 2, fixed 2`, and handed back `archived` with a `LIVE` command of the copy's Live Scenario
- **THEN** the copy's metrics hold `review_after_last_edit: true`, `review_rounds: 2`, `important: 1`, `live_in_scenario: true`, `analyze_findings: 6`

#### Scenario: A guess without review
- **WHEN** a fixture copy is merged with green oracle tests, its orchestrator edited code after a `Review:` agent whose result has an `Important` finding and ran no `Review:` after that, and its `LIVE` command is not in its Live Scenario
- **THEN** `review_after_last_edit` and `live_in_scenario` are `false`, `analyze_findings` is `null`

#### Scenario: A missing journal
- **WHEN** a done change's orchestrator journal is not found
- **THEN** its five signals and `important_sources` are `null` and the exit code is as without the signals (0 when every session log is found)

#### Scenario: Subagents of the new roles
- **WHEN** the fixture session has one `Lookup:`, one `Attack:`, one `Judge:` and one `Check:` agent
- **THEN** the subagent count by role holds `lookup: 1`, `attack: 1`, `judge: 1`, `check: 1`

### Requirement: What the review signals read
Signals SHALL read the journal of the last orchestrator (by its first line) whose final message has `STATUS: archived`, and the `Review:` agents it launched. A review with an empty final message failed and SHALL not count; `review_rounds` counts the rest, `important` their Review verdict count. `review_after_last_edit` SHALL be `false` when a code edit has no counted review after it, unless the last counted review came after a code edit and found no `Important`.

#### Scenario: A handed-back report
- **WHEN** the orchestrator's status and a reviewer's findings are only in the `message` of their `SubagentHandback` calls
- **THEN** the signals read them there as from a final text

#### Scenario: Nit fixes after a clean review
- **WHEN** the orchestrator edited code after its last counted `Review:`, whose result has only `Nit` findings
- **THEN** `review_after_last_edit` is `true`: spec-next allows Nit fixes without a new round

#### Scenario: No review at all
- **WHEN** the orchestrator edited code and launched no `Review:` agent
- **THEN** `review_after_last_edit` is `false`

#### Scenario: No code edit
- **WHEN** a done change's orchestrator edited only files under `solo-sdd/` and `docs/`
- **THEN** `review_after_last_edit` is `true`: the archive gate asks no review

#### Scenario: Words that are not signals
- **WHEN** a review result says "no Important findings", and one `Review:` agent ended with an empty result before its rerun
- **THEN** `important` does not count that sentence, and `review_rounds` does not count the empty run

#### Scenario: One finding named twice
- **WHEN** a review result names `Important A` in its summary and again in its detail, and says `Important 1: closed.` of a finding of an earlier round
- **THEN** `important` counts that result as 1

### Requirement: Review verdict count
A counted review SHALL count `<n>` when its last non-blank line, without `*` and backquotes, is exactly `Important: <n>`, else its lines labelled `Important`. `important` SHALL sum the counted reviews: a finding open over two rounds counts twice. `important_sources` SHALL name `line` or `text` per one. A review launch SHALL pair with the journal whose `.meta.json` `toolUseId` is its id; one refused (an error result) is an empty review, any other unpaired one makes the review signals `null`.

#### Scenario: The verdict line wins
- **WHEN** a counted review result states its one finding only in prose a label reader cannot see and ends with the line `Important: 1`
- **THEN** that review counts 1 and `important_sources` holds `line` for it

#### Scenario: An older review
- **WHEN** a counted review result has `- Important: requirement A is not met` and no line `Important: <n>`
- **THEN** that review counts 1 and `important_sources` holds `text` for it

#### Scenario: Forms of the line
- **WHEN** a review result ends with `**Important: 0**` and a blank line, or ends with `Important: none`, or has `Important: 2` followed by a note
- **THEN** the first counts 0 from `line`; the other two fall back to `text`

#### Scenario: A refused review launch
- **WHEN** the orchestrator's second `Review:` launch has no journal and its tool result is an error, and the first review ends with `Important: 0`
- **THEN** the second is an empty, failed review: `review_rounds: 1`, `important: 0`, `important_sources: ["line"]`

#### Scenario: A review journal not found
- **WHEN** the orchestrator launched `Review: a` and no subagent `.meta.json` holds that launch's `toolUseId`
- **THEN** `review_after_last_edit`, `review_rounds`, `important` and `important_sources` are `null`

### Requirement: What the status and analyze signals read
A code edit SHALL be a file edit or a Bash edit of the orchestrator journal under the status `WORKTREE` or the copy, outside `solo-sdd/` and `docs/`, read as the archive gate reads the journal. `live_in_scenario` SHALL check the status `LIVE` command against the Live Scenario of `verification.md` in the copy's archive of the replayed change by `accept`'s reader, never running it. `analyze_findings` SHALL be `<n>` of the last orchestrator line `Analyze: <n> findings`.

#### Scenario: A Bash edit and an edit outside
- **WHEN** the orchestrator changed a code file of `WORKTREE` by a Bash command with `bashEditDiff` after its last review, and wrote a file in its scratchpad
- **THEN** the Bash edit counts as a code edit and the scratchpad file does not

#### Scenario: Live and analyze sources missing
- **WHEN** the status has no `LIVE` field, or the copy's archive has no `verification.md` or no Live Scenario section, or the orchestrator wrote only `Analyze: off (solo-sdd/config)`
- **THEN** `live_in_scenario` is `null` in the first three cases, `analyze_findings` is `null` in the last

### Requirement: Path marks in the comparison
`compare` SHALL mark a done change `done, path incomplete` when `review_after_last_edit` or `live_in_scenario` is `false`, otherwise `done, path unknown` when either is `null` or the copy has no metrics; the mark SHALL not change what counts as done. The report SHALL list under `Path:` every done change and run with its five signals and `important_sources`.

#### Scenario: Marks in the table
- **WHEN** `compare` runs over the honest and the guess copies
- **THEN** the table shows `done` for the honest change and `done, path incomplete` for the guess, both count as done per run, and `Path:` holds a line per change and run with `review_after_last_edit`, `review_rounds`, `important`, `live_in_scenario`, `analyze_findings` and `important_sources`

#### Scenario: Unknown path
- **WHEN** a done change's signals are `null`
- **THEN** the table shows `done, path unknown`

#### Scenario: A false and an unknown signal
- **WHEN** a done change has `review_after_last_edit: false` and `live_in_scenario: null`
- **THEN** the `compare` table shows `done, path incomplete`
