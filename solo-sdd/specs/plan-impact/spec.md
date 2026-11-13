# plan-impact Specification

## Purpose
A change's `Impact` section and the links between open changes are written so that the dispatcher reliably determines from them which changes can run at the same time.

## Requirements

### Requirement: Impact names files
`spec-plan` SHALL write in the `Impact` section in backquotes only paths of files and directories the change creates, changes or deletes, relative to the project root; function names, commands, words and languages without backquotes. `spec-analyze` SHALL mark a backquoted value in `Impact` that is not a path as a MEDIUM finding and fix it.

#### Scenario: Words in Impact
- **WHEN** `Impact` has `` `en` ``, `` `ru` `` and `` `council_resume` ``
- **THEN** `spec-analyze` marks three MEDIUM findings and removes the backquotes from them

### Requirement: Same requirement means dependency
`spec-analyze` SHALL compare the deltas of the checked change with the deltas of all open changes of the project: if two changes modify a requirement with the same name in the same capability, and neither names the other in `Depends On`, it is a HIGH finding; the fix is to add the earlier one to the `Depends On` of the later one by number or name and record the decision in `Decisions Without Owner`. `spec-plan` SHALL check the same for the changes it creates.

#### Scenario: Two deltas of one requirement
- **WHEN** `171-mcp-consensus-resume-message` and `184-detached-mcp-resume` are open, both modify the requirement "MCP continuation plan and launch" of the capability `mcp-server`, both have `Depends On` `none`
- **THEN** `spec-analyze` marks HIGH and adds `171-mcp-consensus-resume-message` to the `Depends On` of `184-detached-mcp-resume`

### Requirement: Sibling delta after archive
If `solo-sdd archive` of a change prints `sibling: <change> MODIFIED <requirement>`, `spec-next` SHALL carry the scenarios the archive added to that requirement into the sibling change's MODIFIED block without other edits of its text, record the decision as a line in `Decisions Without Owner` of its `verification.md` and run `solo-sdd validate --all`.

#### Scenario: A second change on the same requirement
- **WHEN** `chars-bytes` is archived and added the scenario "Byte mode" to the requirement "Character count command", and the open `chars-empty` modifies the same requirement without this scenario
- **THEN** the scenario "Byte mode" is copied into the MODIFIED block of `chars-empty`, its `verification.md` has a decision line, `validate --all` passes, `chars-bytes` is handed back as `archived`

#### Scenario: A removed or renamed requirement
- **WHEN** the archive removed or renamed the requirement the `sibling:` line names
- **THEN** `spec-next` copies no scenario, runs `solo-sdd validate --all`, and its delta error on the sibling change stays a reason for the status "not done"

#### Scenario: Another error of another change
- **WHEN** after the archive `validate --all --strict` fails on another open change for another reason
- **THEN** it is not fixed this way and stays a reason for the status "not done"
