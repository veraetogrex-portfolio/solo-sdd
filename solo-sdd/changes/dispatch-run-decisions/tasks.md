## 1. Implementation

- [ ] 1.1 Rows in `tests/test_skill_commands.py` named after Run decisions on file and Run decisions after a summary: the skill names the heading, the write before the recalculation, the file choice by `git ls-files`, the heading at the start of the run, the reread of the last section after a summary and the report line; they fail on the current skill
- [ ] 1.2 `skills/spec-dispatch/SKILL.md`: step 9 writes each answer with its key, step 0 appends the run's heading (creating `docs/waiting.md` from the template when missing), step 2 rereads the last section after a summary, the "Decisions without questions" table gets the row for a summary, the report form gets `Run decisions: <file> — <lines> | none`; the rows of 1.1 pass
- [ ] 1.3 `templates/docs/waiting.md`: one line saying that a dispatcher run keeps its decisions under `## Run decisions <date> <time>` below the table; `python3 tests/test_init.py` passes
- [ ] 1.4 `tests/stands/run-decisions.py` for step 1 of the Live Scenario; it prints `run-decisions: <n> of <n> checks passed`

## 2. Acceptance

- [ ] 2.1 Run the Live Scenario (or its Fallback) from verification.md and record the Result, Not Verified and Decisions Without Owner sections
- [ ] 2.2 Run `solo-sdd validate dispatch-run-decisions` and archive the change with `solo-sdd archive dispatch-run-decisions --yes`
