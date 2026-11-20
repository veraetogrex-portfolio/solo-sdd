## MODIFIED Requirements

### Requirement: Review before archive
`guard` SHALL refuse a Bash command that runs `solo-sdd archive <id>` when the actor's transcript (the session's, or for a subagent call its own `subagents/agent-<id>.jsonl`) has an edit (`Write`, `Edit`, `MultiEdit`, `NotebookEdit` or a Bash edit) of a file of the working copy outside `solo-sdd/` and `docs/`, and no `Agent` call whose description starts with `Review:` comes after the first such edit; the reason SHALL name that file. Otherwise the command SHALL pass.

#### Scenario: No review
- **WHEN** the session edited `src/app.py` and ran no `Review:` agent, then runs `solo-sdd archive add-words --yes`
- **THEN** the command is refused, the reason names `src/app.py`

#### Scenario: A review only before the code
- **WHEN** a `Review:` agent ran before the session's first edit of `src/app.py` and none after it
- **THEN** the archive is refused

#### Scenario: Fixes after the review
- **WHEN** a `Review:` agent ran after the first code edit, and the session then fixed `Nit` findings in `src/app.py`
- **THEN** the archive passes: the rounds of `spec-next` decide on re-review, not the guard

#### Scenario: Only artifacts after the review
- **WHEN** after the `Review:` agent the session edited only `solo-sdd/changes/add-words/tasks.md`
- **THEN** the archive passes

#### Scenario: A Bash edit
- **WHEN** the session wrote `src/app.py` only through a Bash heredoc and ran no `Review:` agent
- **THEN** the archive is refused, the reason names `src/app.py`

#### Scenario: An orchestrator subagent
- **WHEN** an orchestrator subagent edited `src/app.py`, launched a `Review:` agent after it and runs the archive, while the main session ran no review
- **THEN** the archive passes: the orchestrator's own transcript decides

#### Scenario: An unreadable transcript
- **WHEN** the transcript file is missing or cannot be read
- **THEN** the command passes and the error is written to the hook error log, as for every hook failure

#### Scenario: Another outside-check role after the code
- **WHEN** after the first edit of `src/app.py` the session ran only `Analyze:`, `Attack:`, `Judge:` or `Check:` agents, then runs `solo-sdd archive add-words --yes`
- **THEN** the archive is refused, the reason names `src/app.py`: only a `Review:` agent counts as the code review
