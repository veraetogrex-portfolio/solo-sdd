---
name: spec-plan
description: Use when the user hands over a plan, a roadmap, a list of bugs or problems, or the conclusions of a discussion and wants it turned into changes - "describe the implementation plan as specs", "split it into a specification", "decompose the changes as much as possible", "write a spec for…", "collect all unsolved problems and split them into sets", "log the bugs and make changes", "create new changes", "fix this bug", "make a fix" - or complains that one large spec was created instead of several small ones.
---

# spec-plan: from a plan or a problem list to a queue of small changes

The result is a set of changes, each of which closes in one `/spec-next` run. No code is written, except the light path items of step 1a, after the plan commit.

## Order

0. **Legacy tree.** The project has `openspec/` and no `solo-sdd/`: stop before any change work, change no file and name the next step `solo-sdd import openspec`; do not import by yourself.
1. **Context.** The local project rules, `solo-sdd/project.md` (intent, mode), `solo-sdd list --json`, `solo-sdd list --specs`, the project's `DESIGN.md` if there is one. This avoids duplicates of existing changes and specs. The prose of every artifact is in `solo-sdd config get artifacts.language` (default `en`); headings, `SHALL`, `WHEN`, `THEN`, keys and paths stay English.
1a. **Light path.** Before any unit, take out two kinds of input item; they get no change. An item already closed by a `light:` commit (its subject starts with the text of `solo-sdd config get commit.light-prefix`, default `light:`, no `solo-sdd/` tree or no command: `light:`, matched as plain text:
   `LP="$(solo-sdd config get commit.light-prefix 2>/dev/null)" || LP=light:; git log --format='%s%x09%h' | LP="$LP" awk 'index($0, ENVIRON["LP"]) == 1'`;
   the older form for the default prefix: `git log --oneline --grep='^light:'`) is counted with its hash.

   An item within the light path bounds of the global rules (no behaviour a main spec describes, no dependency, data, migration or deploy, at most `solo-sdd config get process.light-path.max-files` files; `solo-sdd config get process.light-path` is `off`: no item is light) is done after step 9 by the global rules: the edit, the tests, a live check, one `light:` commit (`commit.light-prefix`). An input made only of such items creates no change and skips steps 2-9.
2. **Units.** Split the input into units. A unit fits when all four conditions hold:
   - one result the user can check themselves;
   - one area of code;
   - at most `solo-sdd config get process.max-tasks` tasks (default 10; a bug fix: the smaller of it and `solo-sdd config get process.bugfix-max-tasks`, default 5);
   - there is a live check scenario.
   
   Group bugs by a common cause or area, not one per change.
2a. **Codebase map.** No `docs/codebase/` (`test -d docs/codebase` fails): the map is not read, the report has `Map: none`. Otherwise each unit reads only the map files of its type row, never the whole map; a unit of several types reads the union of their rows, each file once; a type not in the table reads `ARCHITECTURE.md` only. A file already read for an earlier unit is not read again, but the report still names it for every change whose row has it.

   | Unit type | Map files in `docs/codebase/` |
   |---|---|
   | interface | CONVENTIONS, ARCHITECTURE |
   | API, backend | ARCHITECTURE, CONVENTIONS |
   | database, schemas | ARCHITECTURE, STACK |
   | tests | CONVENTIONS |
   | external integrations | STACK |
   | refactoring | CONCERNS, ARCHITECTURE |
   | configuration | STACK, ARCHITECTURE |
   | bugfix | ARCHITECTURE, CONCERNS |
   | other | ARCHITECTURE |

   Stale map: from the project root run once for the map files read (`<files read>` as paths, `docs/codebase/ARCHITECTURE.md …`): `for f in <files read>; do h=$(sed -n 's/^Commit: \([0-9a-fA-F]*\).*/\1/p;q' "$f"); if [ -n "$h" ] && git merge-base --is-ancestor "$h" HEAD 2>/dev/null; then n=$(git rev-list --count "$h..HEAD" -- . ':!docs' ':!solo-sdd'); if [ "$n" -gt 20 ]; then echo "Map stale: $f, $n commits since $h; refresh: /project-init map"; fi; else echo "Map stale: $f, unknown commits since ${h:-none}; refresh: /project-init map"; fi; done`.

   It counts the commits since the file's `Commit:` stamp that change files outside `docs/` and `solo-sdd/`; more than 20, a stamp commit that is not an ancestor of `HEAD` (rebased away, another branch, unknown) or no stamp prints the line. Every printed line goes into the report as is; planning goes on with the map, it is not refreshed here.
3. **Order and dependencies.** What must be archived earlier. Names follow the project's pattern (in a project with numbers, continue the numbering); `solo-sdd new` takes only a kebab-case id (`add-csv`, `12-fix-export`) that is neither open nor archived.
4. **Check against the intent.** A unit that leads away from the intent in `solo-sdd/project.md` does not become a change: put it into the report as a separate line.
5. **Creation.** Read `creation.md` each time this step starts, also after compaction: for every unit `solo-sdd new <name>`, then the artifacts in order by the "Writing rules" section, with what each must hold.
6. **External conditions.** Access, a key, a person or a paid call is needed: write it into `Needs`. A change made up entirely of such conditions gets a `WAITING` file and a line in `docs/waiting.md`. The user's business facts under placeholders (step 5) does not give `WAITING`.
7. **Check.** `solo-sdd validate --all`.
7a. **Cross-check.** The `spec-analyze` skill on every created change; edits only in the artifacts. Then repeat step 7. `solo-sdd config get process.analyze` is `off`: no cross-check, the report's `Analyze:` line is `Analyze: off (solo-sdd/config)`. An agent changes `process.max-tasks`, `process.bugfix-max-tasks`, `process.requirement-max-chars`, `process.audit-every` and `process.analyze` only on the owner's words in the chat.
8. **Coverage.** Match every input item with a change or with the light path of step 1a (its commit, or `to do` until the commit after step 9). Any other item without a change is an error: create a change or explain in the report why there is none.
9. **Plan commit.** Read `plan-commit.md` each time this step starts, also after compaction: after gate G1 (steps 7, 7a, 8), the plan commit on `plan/<first id>` (`plan/`: `solo-sdd config get delivery.plan-prefix`) under `delivery.mode` `pr` or on the main branch under `local`.

More than five changes: you write the artifacts yourself; Codex executors only if the user named `codex-orchestration` or the project sets `agents.executor: codex`.

## Writing rules

`solo-sdd new <name>` lays out `proposal.md`, `verification.md` and `tasks.md` from templates and prints the path of the delta template; a delta goes into `specs/<capability>/spec.md` by that template. HTML comments in them are hints and never count as content. `solo-sdd validate` accepts a change by these rules:

- `proposal.md`: the sections `## Why`, `## What Changes`, `## Capabilities` (with `### New Capabilities` and `### Modified Capabilities`), `## Impact`, `## Out of Scope`, `## Depends On`, `## Source`; every one except `Capabilities` holds text.
- Deltas: one `specs/<capability>/spec.md` per capability named in `Capabilities`. A capability without a main spec (`solo-sdd/specs/<capability>/spec.md`) starts its delta with `## Purpose` of at least 50 characters; an existing one has no `## Purpose`. `## MODIFIED Requirements` copies the whole block of the main spec under the same requirement name, with every scenario it had, and then changes it; `## REMOVED Requirements` holds one `### Requirement: <name>` per removed name; `## RENAMED Requirements` a `- FROM: ### Requirement: <old>` line and then a `- TO: ### Requirement: <new>` line.
- A change without deltas (documents only) has no `specs/` and writes a bare line `Specs: none` (not a list item) under `## Capabilities`.
- Every requirement under `## ADDED` or `## MODIFIED Requirements` has at least one `#### Scenario:` with a `- **WHEN** …` (or `GIVEN`) and a `- **THEN** …` step.
- `verification.md`: `## Live Scenario` (steps on real input, each with the command or action and the expected output, up to what the user sees), `## Needs` (access, keys, paid calls with count and cost, or `none`), `## Fallback` (how each need is replaced) hold text; `## Result`, `## Not Verified` and `## Decisions Without Owner` keep their placeholders until `/spec-next`.
- `tasks.md`: at most `process.max-tasks` tasks `- [ ]` (default 10), each with the test or command that proves it and doable by the agent alone; anything waiting for a person, access or a paid approval goes into `Needs`, not into a task. A requirement that states an invariant ("never", "always", "at most one", order kept), a round trip or idempotence gets a property-based test task (Hypothesis for Python, fast-check for TypeScript) named after the requirement; the task proves the test fails on a code mutation and its generator reaches the boundary states.
- Tests in `tasks.md` prove behaviour, so the suite grows with behaviour only:
  - A scenario the Live Scenario stand proves needs no second test of the same behaviour; a new case of a tested behaviour is a new row of that test's table, not a new test function. A property test pass 3a of `spec-analyze` requires and a bug fix's test of the bug scenario are not repeats.
  - No test for code without a behaviour of its own: a getter, a DTO, configuration, a thin library wrapper, a private function a scenario test reaches, a one-off script (a stand checks it), what a separate CI step checks.
  - Test doubles only for external I/O (the network, paid APIs) and the clock; the project's own storage gets a temporary real one (a temporary database file) or an in-memory fake; the module under test is never mocked.
  - An assertion of an existing test is changed or deleted only by a task that names a MODIFIED or REMOVED requirement; a task that changes a test's setup, cost or layout names the test and keeps every assertion.
  - A property test that starts a process or creates a repository per example states its example count (`max_examples`) in its task and in the test, the same number in both.
- The last group of `tasks.md` is `## <n>. Acceptance` with exactly two tasks: run the Live Scenario (or its Fallback) and record `Result`, `Not Verified` and `Decisions Without Owner`; then `solo-sdd validate <id>` and `solo-sdd archive <id> --yes`.

## Bug fix

The input is one bug or several with a common cause, and the cause is already found. A bug in behaviour a main spec describes always gets a bug fix change, however small the edit; only a bug outside every spec and within the light path bounds goes without one. The change is shorter than usual, but has the same artifacts, so the usual `/spec-next` runs it further.

1. **The cause before the change.** Needed: a reproduction (what is done → what was expected → what was got) and the place in the code where the result first diverges from the expectation. None: `debug-profile` first; a guess is not written into the proposal. The map is read by step 2a of the "Order" section, the bugfix row.
2. **proposal.md.** Why: the reproduction and the cause with `file:line`. What Changes: only removing the cause. Out of Scope: side improvements, refactoring and neighbouring symptoms, one line each. Source: the user's message about the bug verbatim. A bug fix gets no Design Read.
3. **Spec.** A bug means the spec did not describe this case or the code drifted from it. The bug scenario is added to the spec: a MODIFIED Requirement (whole, with all previous scenarios) with a new scenario, or ADDED if the behaviour was not described at all. The length rule from step 5 applies here too: a `MODIFIED` long requirement is shortened in the same delta. A bug fix is not created without a delta spec: the spec would not catch the next such bug either.
4. **verification.md.** The Live Scenario is the reproduction steps: on the previous code they give the error, after the fix the expected result. In a UI bug fix, a list "element → action → result" only for the affected elements.
5. **tasks.md.** At most `process.bugfix-max-tasks` tasks (default 5), never more than `process.max-tasks`. The first is a test for the bug scenario, named after the Requirement and failing on the current code. Then the fix of the cause and, if needed, one more task; the last group is `Acceptance`. If the change code reads foreign input (step 5 of the "Order" section), this one more task is the tests on hostile input. If its slot is needed for other work, the items are added to the existing test task.
6. **Closing.** Steps 7-9 of the "Order" section.

The name follows the project's pattern, with the word `fix`. If the cause touches more than one area of code, it is not a bug fix but an ordinary plan unit.

## No questions

Do not agree the split before creation. Create, show the report; the user will correct it in words. Interpret an unclear input item by the project's intent and note the interpretation in the report.

## Report

```
Changes created: <n>

| # | Change | Result for the user | Depends on | Tasks |

Map: <change> — <map files of its type rows>, one line per change | Map: none
Map stale: <file>, <n> commits since <hash>; refresh: /project-init map (one line per printed stale file, no line otherwise)
Analyze: CRITICAL <n> · HIGH <n>, fixed <n> | Analyze: off (solo-sdd/config)
Coverage: <input items> of <input items>; light path: <item — `light:` <hash> | to do> | none; without a change: <item — reason> | none
Plan: commit <hash> | commit <hash> on plan/<id>, PR <url> | commit <hash> on plan/<id>, PR <url>, waits for human merge | plan outside git | no change: light path only (plan/: the delivery.plan-prefix value)
Waiting for external conditions: <change — what is needed> | none
My interpretations: <item — how I understood it> | none
Next: /spec-next | /spec-next after the merge of <PR url> | the light path items
```

## Mistakes

| Mistake | Fix |
|---|---|
| One change for the whole plan | Split until each fits `process.max-tasks` tasks and one result |
| A change per bug | Group by cause |
| Retelling the request in your own words in `Source` | Only a verbatim quote |
| Dependencies in the task text | Only in `Depends On` |
| A bug fix without the bug scenario in the spec | The scenario is added through MODIFIED or ADDED, otherwise the bug comes back |
| A requirement longer than `process.requirement-max-chars` (500) | Examples into scenarios, behaviours into separate requirements; `MODIFIED` is shortened in the same delta |
| A scenario without a WHEN/GIVEN or THEN step, a section like `## DEPRECATED Requirements` in a delta | Steps `**WHEN**` (or `**GIVEN**`) and `**THEN**` in every scenario; only the sections ADDED, MODIFIED, REMOVED, RENAMED Requirements |
| Dials derived from the user's words | Only a `Dial` line with three numbers, otherwise 1/1/1 and the mark "draft without direction" |
| Invented reviews or numbers in tasks | The placeholder `[data needed: …]` and `Needs` |
| The Live Scenario of a UI change described in general words | A list "element → action → result", widths 1280 and 390, every theme |
| The change reads foreign input, and there is no task on hostile input | One test task with the applicable items of the list from step 5 |
| Read the whole `docs/codebase/` for every unit | Only the files of the unit's type row from step 2a |
| Stopped or refreshed the map because it is stale | The `Map stale` line in the report, planning goes on |
| Started writing code | This skill ends at the plan commit; only the light path items of step 1a are done after it |
| Committed the whole tree | The commit holds only the folders of created and changed changes |
