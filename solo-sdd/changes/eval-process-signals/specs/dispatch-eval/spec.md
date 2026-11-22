## ADDED Requirements

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
A counted review SHALL count `<n>` when its last non-blank line, without `*` and backquotes, is exactly `Important: <n>`, else its lines labelled `Important`. `important` SHALL sum the counted reviews: a finding open over two rounds counts twice. `important_sources` SHALL name `line` or `text` per one. A review launch SHALL pair with the journal whose `.meta.json` `toolUseId` is its id; an unpaired one makes `review_after_last_edit`, `review_rounds`, `important`, `important_sources` `null`.

#### Scenario: The verdict line wins
- **WHEN** a counted review result states its one finding only in prose a label reader cannot see and ends with the line `Important: 1`
- **THEN** that review counts 1 and `important_sources` holds `line` for it

#### Scenario: An older review
- **WHEN** a counted review result has `- Important: requirement A is not met` and no line `Important: <n>`
- **THEN** that review counts 1 and `important_sources` holds `text` for it

#### Scenario: Forms of the line
- **WHEN** a review result ends with `**Important: 0**` and a blank line, or ends with `Important: none`, or has `Important: 2` followed by a note
- **THEN** the first counts 0 from `line`; the other two fall back to `text`

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

## MODIFIED Requirements

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
