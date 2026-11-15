## ADDED Requirements

### Requirement: Run decisions on file
Every owner answer that changes the plan of a dispatcher run (a shared path, an ignored dependency, a kept marker or dependency, the orchestrator limit, the order, taking or dropping changes) SHALL be written before the next plan recalculation, one line with the key it gives the planner, under `## Run decisions <date> <start time of the run>` in `docs/waiting.md` when git does not track it, else in `solo-sdd/run-decisions.md` of the git common folder.

#### Scenario: A shared path answer
- **WHEN** the owner answers "Treat package-lock.json as shared until the end of the run"
- **THEN** before the next recalculation `docs/waiting.md` has the run's section with a line holding `--shared package-lock.json`

#### Scenario: A tracked waiting file
- **WHEN** git tracks `docs/waiting.md` of the main folder and the owner answers a run question
- **THEN** the line goes to `solo-sdd/run-decisions.md` of the git common folder, and `git status --porcelain --untracked-files=no` of the main folder stays empty

#### Scenario: A kept marker
- **WHEN** the owner answers "Keep" to the abandoned marker question
- **THEN** the section has a line naming the change and that the marker is kept, and the question is not asked again in this run

### Requirement: Run decisions after a summary
At the start of a run, before the first plan, the dispatcher SHALL append its run's heading, so its section is the last `## Run decisions` section of the file. After a context summary, before the next recalculation, it SHALL reread that last section and pass every key it holds; earlier sections SHALL NOT be read. The report SHALL name the file and the lines of the section.

#### Scenario: Keys survive a summary
- **WHEN** the section holds `--shared scripts/build-catalog.mjs` and the context was summarised
- **THEN** the next `sdd-dispatch-plan.py` call has `--shared scripts/build-catalog.mjs`, and the changes held by that path are in `launch:`

#### Scenario: No waiting file yet
- **WHEN** the main folder has no `docs/waiting.md` and git does not track that path
- **THEN** the run creates it from the `docs/waiting.md` template and appends its heading after the table

#### Scenario: An older run
- **WHEN** `docs/waiting.md` holds a run decisions section of an earlier run with `--ignore-dep a:b`
- **THEN** the new run passes no `--ignore-dep a:b` unless its own section holds it
