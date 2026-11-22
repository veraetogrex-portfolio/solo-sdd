## Live Scenario

`python3 tests/stands/goal-first.py prepare` copies `examples/demo` into a fresh `/tmp/goal-first.*` folder, runs `git init` there with one commit (`delivery.mode: local` is the demo's own), sets `process.analyze: off` (the stand grades planning, not the cross-check) and `process.light-path: off` (a removal of two tests in one file is a light path item, which makes no change) in the copy's `solo-sdd/config`, makes `test_usual_bill` of `tests/test_tip.py` slow (a sleep of 2 s), and writes two prompts next to the copy: `plan.md` (the repository's whole `global/AGENTS.md`, the `spec-plan` text with its step files joined, and the request "remove the tests test_usual_bill and test_not_a_number") and `outside.md` (the repository's whole `global/AGENTS.md` and the request "rename the tests test_usual_bill and test_not_a_number"); it prints `copy: <path>` and the two prompt paths. `clean <copy>` removes a copy `prepare` made and refuses any other folder.

Every answer comes from a Claude Code subagent of the lead session on `agents.test-model` (`haiku`), never `claude -p`. Under the dispatcher the hook allows only tagged subagents from a subagent, so each runs as `Lookup: goal-first <prompt>` with `subagent_type: Explore`: it reads the copy and writes nothing, so the prompt asks it to return every file the plan would create as a block `=== <path from the copy root>` followed by the file's text, and then `=== report` and the plan report. The lead saves the answer to the scratchpad.

`--grade <answer>` reads the blocks and prints five lines `<label>: yes|no`, matching each line after Markdown markers (`*`, `` ` ``, `_`, a list or quote marker) are stripped and whitespace is collapsed: `goal in Why` (the last two non-empty lines of the `## Why` section of the `proposal.md` block start with `Goal:` and `Check:`), `check with a number` (that `Check:` line holds a digit), `inferred marked` (both lines hold `(inferred)` and the `## Decisions Without Owner` section of the `verification.md` block has a line holding `goal inferred:`), `both steps have tasks` (each of `test_usual_bill` and `test_not_a_number` is named by a `- [ ]` line of the `tasks.md` block) and `Proposals names test_not_a_number` (a line of the `report` block starting `Proposals:` names `test_not_a_number`; `n/a (the check names no time)` when the `Check:` line names no time unit, since only a time goal makes the fast test a step that does not move the check). `--grade-report <report>` prints `goal first: yes` when the first two non-empty lines of the report, normalised the same way, start with `Goal:` and `Check:` and both hold `(inferred)`. A missing block, an unreadable file or a wrong argument exits 1.

1. `python3 sync.py status` → `outdated` for exactly the edited deployed files (`spec-plan` with the new `report.md`, the three copies of `global/AGENTS.md`), no unexpected `drift`; `sync.py push` is left to the delivery after merge, as in `source-over-paste`.
2. A subagent gets `plan.md` with the copy as its project folder → `--grade <answer>` prints `goal in Why: yes`, `check with a number: yes`, `inferred marked: yes`, `both steps have tasks: yes`, `Proposals names test_not_a_number: yes` (an `n/a` leaves the scenario A step that does not move the check unproven: a `Not Verified` line); the answer is kept as `tests/stands/goal-first/live-plan.md`.
3. A subagent gets `outside.md` with the copy as its project folder → `--grade-report <report>` prints `goal first: yes`; the report is kept as `tests/stands/goal-first/live-report.md`.
4. The recorded run and the references: `python3 tests/stands/goal-first.py --grade tests/stands/goal-first/live-plan.md` → the five `yes` lines of step 2; `expected-plan.md` gives the same five, `wrong-plan.md` gives `goal in Why: no`; `--grade-report` on `live-report.md` and `expected-report.md` gives `goal first: yes`, on `wrong-report.md` `goal first: no`.

## Needs

none

## Fallback

Not needed: the stand runs locally, the subagents run in the lead session on the subscription.

## Result

<!-- Filled during apply: date, what was run, what was observed. -->

2026-11-22, worktree of branch `change/goal-first`, the orchestrator (a dispatched subagent on Opus) as the lead; 16 stand runs as `Lookup:` Explore subagents on `haiku`, no `claude -p`, no paid API call. The Live Scenario did NOT pass; the change is not archived.

- Plan runs (step 2), `--grade` on each answer: run 1 (first wording) five `yes`, kept as `tests/stands/goal-first/live-plan.md`; run 2 no `Goal:` line; run 3 four `yes` and `Proposals ...: n/a (the check names no time)` (goal: a smaller suite, check `Ran 2 tests`); runs 4, 5, 6 no `Goal:` line (all three said no reason was given); runs 7, 8, with `Goal:`/`Check:` lines tried at the top of the report form, wrote `Goal: none (the request names its goal)` and no Why lines, so that form was rolled back. On the final text: 1 of 4 runs (run 3) has the Why lines.
- Outside runs (step 3), `--grade-report`: run 1 `Goal: rename the two tests as requested` (the steps restated, no `(inferred)`); run 2 `Check:` without `(inferred)`; run 3 the lines came before the stand's `=== report` block; run 4 refused to describe edits it could not make; runs 5-8 on a `renamed` copy where the work is done: run 6 opened with `Goal:` and `Check:` but `(inferred from the session note ...)`, runs 5, 7, 8 had no goal lines. `goal first: yes` in 0 of 8.
- Text fixes between runs: the goal must not restate the steps, each line on its own line, `(inferred)` inside the line templates, the `proposal.md` template comment and the Writing rules line naming the step 5 rule; none made the haiku runs reliable.
- Cause (not proven): the subagents carry the installed `~/.claude/CLAUDE.md` and `spec-plan` without the rule in their own context, while the new text comes only inside the prompt; the push that would lay out the new text is a prod action left to the delivery after merge, so the stand cannot run on the laid-out text from the branch.
- Step 1: `python3 sync.py status` shows `outdated` for exactly `spec-plan` (`SKILL.md`, `creation.md`), the three `global/AGENTS.md` copies and the `proposal.md` template, `missing` for the new `codebase-map.md`, no `drift`; `sync.py push` is left to the delivery after merge.
- `/usr/bin/python3 tests/run.py --jobs 5 --tier slow` -> `files: 41, failed: 0, seconds: 265.0`; lint silent; `solo-sdd validate --all` 0 errors.
- References: `expected-plan.md` five `yes`, `wrong-plan.md` `goal in Why: no`, `expected-report.md` `goal first: yes`, `wrong-report.md` `goal first: no`; a missing block, an unreadable file and a wrong argument exit 1; `clean` removed every copy.
- `python3 tests/test_skill_commands.py` OK (41 tests); `test_goal_first` fails on the rule text of the base commit. `tests/stands/plan-map-stand.py` prints `9 of 11 checks passed` before and after the move of step 2a (the two failures are on the base commit too).

## Not Verified

<!-- Filled during apply: what stayed unproven and why. Write: nothing - if all proven. -->

- Steps 2 and 3 of the Live Scenario: on `haiku` the plan rule held in 1 of 4 runs on the final text and the outside rule in 0 of 8 (Result). Needed: a run on the laid-out text after `sync.py push` (a prod action, the owner's), or an owner's decision on the stand model or on a firmer form of the rule.
- Independent acceptance (step 7a) was not run: the live scenario failed first.

## Decisions Without Owner

<!-- Filled during apply: choices made without asking, and new changes created for out-of-scope work. -->

- analyze (judge kept HIGH J1): which rules section 6 holds → both: the `Goal:` and `Check:` lines opening the report and the `Proposals:` line; requirement 2 says the line goes into the report (in `spec-plan` the plan report) and section 6 holds it — the proposal said "the same two lines", and outside `spec-plan` a step that does not move the check had no place.
- analyze (MEDIUM J2, J3): grade lines undefined, check without a number → the requirement and creation rule ask for literal `Goal:`, `Check:` (with a number), `(inferred)` and `goal inferred:` lines; the Live Scenario defines what each grade line matches; the grade reads the `Proposals:` line of the report, renamed `Proposals names test_not_a_number`.
- analyze (MEDIUM J4): a reason given for some steps only → a step without a reason takes the goal the request names for the others, else an inferred one (in the creation rule; rejected: a spec requirement, past the 500-char limit).
- analyze (MEDIUM J5, LOW J7): creation.md has no Why item, the move was conditional → task 1.1 adds a new item to step 5 and moves a step body out unconditionally (see the repeat, R6); `tests/affected.json` needs no entry (its `skills/` key holds the file), so it left Impact.
- analyze (MEDIUM J6): nothing compares the result with `Check:` → Out of Scope: the line steers the plan and its proposals; acceptance stays the Live Scenario.
- analyze (LOW J8, J9): "cheaper" has no measure — kept as is, the `Check:` line measures "moves"; the stand model is named as `agents.test-model` (`haiku`).
- analyze: the judge dropped 9 findings (property test, Source paraphrase, Decisions marking task, prod push, field-exists proof, Proposals reader, outside report form, term drift, 11+ steps) with reasons.
- Stand subagents run as `Lookup:` Explore agents on `haiku` and return the files as blocks instead of writing them: under the dispatcher the hook allows only tagged subagents from a subagent, and an Explore agent writes nothing; `sync.py push` is left to the delivery after merge (a push from the branch would lay out unmerged text into prod).
- analyze repeat (CRITICAL R1): the stand's request is a light path item, which makes no change → the stand sets `process.light-path: off` in the copy; a step-only light path item is Out of Scope (rejected: a new scenario for the light path report, beyond this change).
- analyze repeat (CRITICAL R2): section 1 asks a report to start with plain lines → the `Goal:` and `Check:` lines come first and section 1 names it (rejected: the goal lines after the plain lines, which a reader of a long report misses).
- analyze repeat (HIGH R3): the prompts held one section → both prompts hold the whole `global/AGENTS.md`, `plan.md` also the joined `spec-plan`.
- analyze repeat (HIGH R4, R5; LOW R7): one answer for a judgement call, grades looser than the THENs → `Proposals names test_not_a_number` prints `n/a` when the check names no time; the grades check the last two lines of Why, both `(inferred)`, and the first two report lines, each normalised; the scenario THEN names the literal `Proposals:` line.
- analyze repeat (MEDIUM R6): `## Report` is no step → step 2a (Codebase map) moves into `codebase-map.md` instead, and `tests/stands/plan-map-stand.py` reads the joined text.
- analyze repeat (LOW R8): "never into a task or an edit" and `Proposals:` outside `spec-plan` are covered by the text test only; listed.
