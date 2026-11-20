## ADDED Requirements

### Requirement: Process path signals
`sdd-eval.py metrics` SHALL add per copy `review_after_last_edit`, `review_rounds`, `important`, `live_in_scenario` and `analyze_findings`, each `null` when its source is missing. `compare` SHALL mark a done change `done, path incomplete` when either of `review_after_last_edit` and `live_in_scenario` is false, otherwise `done, path unknown` when either is `null`.

#### Scenario: An honest path
- **WHEN** the fixture orchestrator edited code, launched `Review: a` after its last code edit with one `Important` in round one and none in round two, then edited `tasks.md`, reported `Analyze: 6 findings, kept 2, dropped 4; CRITICAL 0 · HIGH 2, fixed 2`, and its `LIVE` command is in the Live Scenario
- **THEN** the copy's metrics hold `review_after_last_edit: true`, `review_rounds: 2`, `important: 1`, `live_in_scenario: true`, `analyze_findings: 6`

#### Scenario: A guess without review
- **WHEN** a fixture copy is merged with green oracle tests, its orchestrator edited code after its last `Review:` agent, and its `LIVE` command is not in its Live Scenario
- **THEN** both signals are `false`, and the `compare` table shows `done, path incomplete` for that change

#### Scenario: A missing journal
- **WHEN** a done change's orchestrator journal is not found
- **THEN** its signals are `null`, and the `compare` table shows `done, path unknown`

#### Scenario: A false and an unknown signal
- **WHEN** a done change has `review_after_last_edit: false` and `live_in_scenario: null`
- **THEN** the `compare` table shows `done, path incomplete`

#### Scenario: No code edit
- **WHEN** a done change's orchestrator edited only files under `solo-sdd/` and `docs/`
- **THEN** `review_after_last_edit` is `true`: the archive gate asks no review

#### Scenario: Subagents of the new roles
- **WHEN** the fixture session has one `Lookup:`, one `Attack:`, one `Judge:` and one `Check:` agent
- **THEN** the subagent count by role holds `lookup: 1`, `attack: 1`, `judge: 1`, `check: 1`

### Requirement: What the signals read
Signals SHALL read the journal of the orchestrator that archived. A code edit SHALL be one the archive gate counts (capability `work-hooks-subagents`, Review before archive); with none, `review_after_last_edit` is `true`. `important` SHALL count findings labelled `Important`, `review_rounds` the `Review:` agents except a rerun after a reviewer failure, and `live_in_scenario` SHALL check the `LIVE` field of the last status block of the orchestrator's final message by the reader `accept` uses.

#### Scenario: Words that are not signals
- **WHEN** the orchestrator wrote `Analyze: off (solo-sdd/config)`, a review result says "no Important findings", and one `Review:` agent was a rerun after a failure
- **THEN** `analyze_findings` is `null`, `important` does not count that sentence, and `review_rounds` does not count the rerun

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
