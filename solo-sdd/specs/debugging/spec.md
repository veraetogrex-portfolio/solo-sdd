# debugging Specification

## Purpose
`debug-profile` diagnoses both a running service and a bug in code, in solo-sdd's own steps, so debugging needs no other plugin.

## Requirements

### Requirement: Code bug path
`debug-profile` SHALL hold a path for a bug in code without a running service, which needs no project profile: reproduce it by a failing test, trace the cause back along the call chain to the first place the value is wrong, compare with a working example, test one hypothesis at a time, and hand the fix to the Bug fix section of `spec-plan` with the reproduction and the place `file:line`. Its description SHALL name a failing test and a wrong function result.

#### Scenario: A failing test
- **WHEN** an agent has a red test and no service runs
- **THEN** the code bug section of `debug-profile` names, in this order, the failing test, the trace back along the call chain, the working example, one hypothesis and the hand-off to Bug fix, and does not send the agent to `docs/debug-profile.md` first

#### Scenario: The skill is found for a code bug
- **WHEN** an agent picks a skill for a test that fails for an unknown reason
- **THEN** the description of `debug-profile` names a failing test and a wrong function result, and the `/debug-profile` entry of `global/AGENTS.md` section 14 names a bug in code

### Requirement: Debugging and planning by own skills
`relay` SHALL send debugging to `/debug-profile`; `global/AGENTS.md` SHALL send debugging to `/debug-profile` and planning to `/spec-plan` and SHALL say that in a project with `solo-sdd/` a plugin's own cycle of tests, verification, per-task subagents and code review is not used: `spec-next` and `ship` set the cycle. Neither SHALL name a plugin skill (a backquoted `plugin:name`).

#### Scenario: A failed check in a relayed report
- **WHEN** `relay` meets a check that failed in another agent's report
- **THEN** its step 4 names `/debug-profile` and no plugin skill

#### Scenario: The orchestration rule
- **WHEN** an agent reads section 10 of `global/AGENTS.md`
- **THEN** it reads "Plan through `/spec-plan`, debug through `/debug-profile`." and the sentence that `spec-next` and `ship` set the cycle, and no plugin name
