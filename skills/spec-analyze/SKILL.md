---
name: spec-analyze
description: Use when change artifacts are written and code is not yet touched - before the first task of /spec-next, after /spec-plan creates changes, or when the user says "check the change before the start", "cross-check the artifacts", "analyze", "are there holes in the spec", "is the change ready for implementation". Checks the change against itself, the main specs and the project intent; fixes the artifacts, never the code.
---

# spec-analyze: checking a change before code

`spec-audit` checks code against the spec when the code is already written. This skill checks the spec against itself while there is no code: a hole in `tasks.md` costs one line, and the same hole after implementation costs a rework.

Argument: the change name. Without an argument, the change `/spec-next` is running now (its `CLAIM`), otherwise all open changes without `WAITING`.

## What to read

0. Legacy tree: the project has `openspec/` and no `solo-sdd/`: stop before any change work, change no file and name the next step `solo-sdd import openspec`; do not import by yourself.
1. The project rules: `AGENTS.md`, `CLAUDE.md`, `solo-sdd/project.md` (the intent). This is the constitution: violating it is always CRITICAL.
2. The change artifacts: `proposal.md`, `specs/*/spec.md`, `verification.md`, `tasks.md`, `design.md` (if any).
3. The main specs of the affected capabilities: `solo-sdd/specs/<cap>/spec.md`.
4. `solo-sdd/analyze.md`, if the project has it: the extra checks of this project. Run them on a par with the passes below.
5. Code only to check an artifact's claim about the current state ("X is not connected now"). No code review is done here.

## Passes

**1. Coverage.** Every requirement and scenario of the delta spec is implemented by at least one task and checked by a test or a Live Scenario step. A scenario a Live Scenario step checks needs no unit test: it counts as covered, no finding. A task without a requirement is extra work or a missed requirement. A REMOVED requirement needs a task to delete the code and tests.

**2. The change frame.** A change without `verification.md` (written before this process): skip this pass, except the "Hostile input" and requirement length items, and note it in the report.
- `Out of Scope` is not empty; the neighbouring changes of the plan are named in it.
- All changes from `Depends On` are already in `solo-sdd/changes/archive/`. Otherwise the change is not ready to start: CRITICAL.
- `Source` is the user's quote, not a retelling.
- At most 10 tasks; the last group is `Acceptance` of two tasks.
- No tasks that wait for a person, access or paid consent: they belong in `Needs`.
- The `Live Scenario` reaches what the user sees (the built artifact, a screen, a service answer), not an internal function. Every `Needs` item has a `Fallback`. A paid call is named with the number and the amount.
- `Impact` has only paths of files and directories in backquotes. A quoted value that is not a path (a function name, a command, a word, a language) is MEDIUM: remove the quotes.
- The text of an `ADDED` or `MODIFIED` requirement in the delta (from `### Requirement:` to the first header, usually `#### Scenario:`) longer than 500 chars is HIGH. Fix: examples and edge cases into scenarios, several behaviours into separate requirements; for `MODIFIED` the behaviour does not change and the previous scenarios stay.
- A bug fix change (`spec-plan`, the "Bug fix" section): Why has a reproduction and the place of the cause `file:line`; the first task is a test for the bug scenario that fails on the current code; at most 5 tasks; side edits are named in Out of Scope. A violation is HIGH.
- Hostile input. The change code reads foreign input (files, archives, documents or network data whose path or content arrive while the program runs: an argument, a request, the network, the user's choice, rather than lying in the project repository), and `tasks.md` has no task of tests on hostile input: HIGH.

  Fix: a separate task of tests on hostile input, even if pass 1 already found the requirements for this input uncovered; it holds the items applicable to this input: a limit on size and number of entries (ZIP bomb, compression ratio), archive entry paths (`..`, absolute, links), nesting depth, XML entity expansion, catastrophic regular expressions, truncated and broken input, escaping when inserting into code, HTML or a command.

  Applicability is decided by the input format, not by the intended parsing method: any archive has entry paths, even if it is not unpacked to disk. An inapplicable item is not written. Only if `tasks.md` already has the maximum number of tasks (10, for a bug fix 5), the items are added to the existing test task. A change that reads only `AGENTS.md`, configs and the project's own files gives no finding.

**3. Checkability.** Every task has an observable criterion: a named test that fails on the current code, a command with the expected output or a Live Scenario step. "The field exists", "the function is called", "the tests are green" do not count as proof.

**3a. Executable properties.** A requirement worded as "for any": an invariant ("never", "always", "at most one", the order is kept), a round trip (parse ↔ build, save ↔ restore) or idempotence (a repeat does not change the result) is checked by a property-based test, not only by examples: `fast-check` in TypeScript, `Hypothesis` in Python. No such task: HIGH. The task must have:
- the Requirement name in the test name;
- proof that the test catches a defect: a code mutation it fails on; a green test on working code proves nothing;
- a generator that reaches boundary states (the retry limit, an empty queue, a repeat after a failure). Short random sequences do not reach them.

A property test complements the `Live Scenario`, it does not replace it.

**4. Consumer.** Every new field, module, setting or report value is named together with whoever reads it. Without a consumer: HIGH.

**4a. Trust boundary.** The change adds a trust boundary: network input (an endpoint, a port, a webhook), authentication or authorization, secrets (keys, tokens, passwords), a command, query or path built from user input, data of several users or tenants. Its spec has no requirement saying who may act and what is refused: HIGH.

Fix: a requirement "who may <action>; any other actor gets <answer>" with a scenario of the refused actor; for a command or a path, which input is refused (outside the folder, a shell metacharacter). A change that adds no boundary gives no finding. Pass 2 "Hostile input" covers parsing foreign input; the code itself is checked by the security pass of `spec-audit`.

**5. Ambiguities.** Where a decision is not made: the boundaries of the area; states and transitions of entities; empty, erroneous and partial cases (no data, an external system failure, a break, a repeated run); telling "no data" from "could not read"; idempotence on a repeat; what the user sees in each outcome; one term named differently in different artifacts. `TBD`, `[NEEDS CLARIFICATION]`, "clarify later": HIGH.

**6. Wording.** A method instead of a property ("look for the substring X" instead of "git history does not change"); places by line numbers instead of structure; hard-coded values that should be asked from the system; words without a measure: "fast", "reliable", "convenient", "if needed", "etc.". MEDIUM if acceptance depends on the wording, otherwise LOW.

**7. Consistency.** The delta spec contradicts the main one without MODIFIED/REMOVED; `design.md` chooses a decision that is not in the tasks; a task uses what appears later; the change leads away from the intent in `solo-sdd/project.md`: CRITICAL.

**7a. Requirement compatibility.** Pass 7 looks for a divergence of the delta spec from the main one, this one for requirements that are true one by one and unsatisfiable together. Look at the whole set at once: the requirements and scenarios of the delta spec plus the main specs of the affected capabilities.

1. Put them into a table `condition → behaviour`: the condition from WHEN, the behaviour from THEN; for a requirement without a scenario the condition is "always". Non-functional constraints (time, size, number of calls, order) are rows too.
2. Compare the rows whose conditions overlap:
   - **contradiction**: under one condition two different behaviours ("on a break retry the request" and "on a break show an error"): CRITICAL;
   - **constraint conflict**: a functional and a non-functional requirement cannot hold together ("the answer holds the whole history" and "the answer is at most 2 KB"): CRITICAL;
   - **a hole at the seam**: both conditions occur separately, and their combination is described by no row (a repeated run on an empty queue): HIGH if the outcome is visible to the user, otherwise MEDIUM;
   - **a hidden assumption**: a behaviour relies on a condition that is in no spec ("the user is already logged in", "the file exists"): HIGH.
3. The fix is as for the other findings: the chosen option into the spec, and into `Decisions Without Owner` what was chosen and which option was rejected.

The table does not go into the report, only the findings. For a change of one or two requirements it takes a few lines, but the pass is still done.

**7b. Overlap with open changes.** Compare the deltas of the checked change with the deltas of all open changes of the project (`solo-sdd/changes/*/specs/*/spec.md`, except `archive`). Two changes modify a requirement with the same name in the same capability, and neither's `Depends On` names the other: HIGH (for example, 171 and 184 both modify "MCP continuation plan and launch" in `mcp-server`).

Fix: add the earlier one to the `Depends On` of the later one by number or name and record the decision in `Decisions Without Owner`; if you edit another change, the record goes into its `verification.md`.

## Levels

| Level | What | Consequence |
|---|---|---|
| CRITICAL | a violation of the intent or the project rules; a requirement without a task; an unarchived dependency | do not start code |
| HIGH | an uncheckable task; no consumer; a trust boundary without a rule on who may act; an unresolved ambiguity that affects behaviour; waiting for a person in tasks | fix before code |
| MEDIUM | a vague criterion; term drift; a task without a requirement | fix if the scope does not change |
| LOW | style, repeats | only list |

## What to do with findings

Ask no questions. Fix CRITICAL and HIGH yourself in the artifacts: a requirement and a scenario in the spec, a decision in `design.md` or a task, waiting in `Needs`. Record every decision as a line in the `Decisions Without Owner` section of `verification.md`: "analyze: <what was unclear> → <what was decided> — <why>". No `verification.md`: into the report.

Do not bypass an unarchived dependency: the change is not ready, `/spec-next` takes another.

Code does not change. After the edits: `solo-sdd validate <change>` and a repeat of passes 1, 2, 7 and 7a: an edit of coverage or the frame often opens a new hole.

## Report

```
analyze <change>: requirements <n>, scenarios <n>, tasks <n>; covered <x>/<n>
CRITICAL <n> · HIGH <n> · MEDIUM <n> · LOW <n>, fixed <n>

| ID | Pass | Level | Where | Finding | What was done |

Ready for implementation: yes | no — <reason>
```

At most 30 rows in the table, the rest as a summary by pass.

## Mistakes

| Mistake | Fix |
|---|---|
| Started editing code | Only the artifacts change here |
| Asked the user | Decide yourself, record in `Decisions Without Owner` |
| Skipped pass 2 because "it is clear anyway" | The change frame is always checked, except a change without `verification.md` |
| "The test will come later" as a criterion | The test or the scenario step is named now |
| Checked the requirements one by one | A contradiction is visible only in a pair: the condition table from pass 7a |
