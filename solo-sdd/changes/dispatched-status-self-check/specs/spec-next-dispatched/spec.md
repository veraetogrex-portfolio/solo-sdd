## ADDED Requirements

### Requirement: Status self-check before handback
In the "Under the dispatcher" mode, before handing back `STATUS: archived` the orchestrator SHALL write its status block to a file outside `WORKTREE` and run `sdd-dispatch.py accept` on it. On code 1 or 2 it SHALL correct the stated field from the command's real output (the `LIVE` text after `->` is one printed line, copied verbatim) or rework the change, and repeat the check. It SHALL hand back `archived` only after `status matches`.

#### Scenario: A paraphrased LIVE line
- **WHEN** the stand prints `settings-ci-wait: 4 of 4 checks passed` and the drafted status says `LIVE: python3 tests/stands/settings-ci-wait.py -> all four checks pass`
- **THEN** the self-check reports the `LIVE` mismatch, the orchestrator copies the printed line into the field, the repeated check gives `status matches`, and the dispatcher gets a status that matches on its first acceptance

#### Scenario: A failing live command
- **WHEN** the self-check reports that the `LIVE` command ended with a non-zero code
- **THEN** the orchestrator does not edit the code into the field: it fixes the change and checks again, or hands back `not_ready` with the failure in `NOTES`
