# Solo SDD: the algorithm

Spec-driven development for one person or a team, with any coding agent (Claude Code and Codex today). The user sets the goal and accepts the result. The agents run the work themselves: from the plan to code merged into main, without questions along the way. The base is solo-sdd's own process tree `solo-sdd/` and its commands (`solo-sdd new`, `validate`, `list`, `archive`); the skills from `skills/` work on top of them. A project still on `openspec/` moves with `solo-sdd import openspec`.

How the repository is organised and how to deploy it is in [README.md](README.md). The third-party files the repository ships are listed in [SOURCES.md](SOURCES.md). Why the rules are worded the way they are is in [LESSONS.md](LESSONS.md).

## Principles

1. **The specification is the source of truth.** Behaviour changes together with the spec, in one change. Code that diverges from the spec counts as a defect, even if the tests are green.
2. **A small change.** One result the user can check themselves, one area of code, at most 10 tasks. If it comes out bigger, it is several changes linked through `Depends On`.
3. **A property, not a method.** The spec says what must be true ("git history does not change"), not how to check it ("look for the substring push"). The implementer chooses the method.
4. **Proof, not a report.** Readiness is confirmed by observations: a test that fails on the previous code, and a live scenario in what a person sees. Green tests, a report by the author or a subagent, "the function was called" do not count as proof.
5. **No questions along the way.** The agent resolves an ambiguity itself and records the decision. Asking is allowed only before three things: a paid call, deleting or overwriting data, an action on prod. The question names what will happen, how many calls and what amount.
6. **A blocker does not stop the work.** First look for a workaround: mocks, old data, `.env`, a neighbouring service. No workaround: what is unchecked goes into `verification.md` and `docs/waiting.md`, the rest gets closed.
7. **Code is written by whoever holds the plan.** Every handoff between agents loses precision, so the lead agent writes the code itself. Subagents are for independent acceptance and heavy reading. Review is done by an agent that did not write this code.
8. **Nothing is invented.** Values the source knows (CLI, API, database) are asked from the source. An honest "could not determine" is better than a plausible value.
9. **Cheap where a mistake is easy to notice.** Search, reading logs and test output run on cheap models; code, review and acceptance on the main one. First the effort changes (medium by default, low for mechanics, higher if stuck), the model only when effort did not help. Paid calls to the product model in tests and runs go to the cheapest models and with consent. Heavy reading goes to a search subagent (Explore), so the lead's context does not get compacted.
10. **"Done" = archived, checked live, merged.** If any of the three is missing, the status is "not done" with what is missing.

## Cycle

```
 0 project-init ─► 1 context-resume ─► 2 evidence-research (when needed)
                                                   │
 9 spec-audit ◄─ 8 ship ◄─ 7 closing ◄─ 6 proof ◄─ 5 spec-next ◄─ 4 spec-analyze ◄─ 3 spec-plan
 (every 5 archives)                        ▲
                                         debug-profile, ui-check, agent-quality
```

Cross-cutting skills at any stage: `work-status` (five lines about the state), `context-resume` (after a pause, a context compaction or an agent switch).

### 0. The project is ready for agents: `project-init`

Once per project. It creates `AGENTS.md` (project rules: commands, map, boundaries and invariants, checks), `CLAUDE.md` with the line `@AGENTS.md`, the process tree `solo-sdd/` by `solo-sdd init` with `solo-sdd/project.md` (language, mode and an "Intent"), `.env.example`, README.

In a repository that already has code it also writes the codebase map `docs/codebase/` (`STACK.md`, `ARCHITECTURE.md`, `CONVENTIONS.md`, `CONCERNS.md`): four cheap subagents, every statement names a path, each file stamped with the commit; the `CONCERNS.md` items are candidates for `spec-plan`. `/project-init map` refreshes it.

**Gate G0:** `solo-sdd validate --all` passes; every command from the `AGENTS.md` table actually runs; the project comes up by the README in a clean shell.

### 1. Context: `context-resume`

When returning to a project, after a context compaction or on an agent switch. It reads the project rules, `handoff.md`, `verification.md` of open changes, `git status` and the history by the words of the task. The output is a map: the goal, the source of truth, the last confirmed state, the user's decisions, blockers, the next step. A fact from history is checked against files and the service. If they diverge, the current state counts as right.

### 2. Research and decision: `evidence-research`

Only when the plan cannot be written without it: choosing a technology, a service or an approach. `evidence-research` gives a table of options by the user's constraints, every fact with a source and a date. A disputed decision goes the same way: the options side by side on checked facts, the choice and its reason. The result goes into `spec-plan` as input.

### Light path: no change

A code edit takes the light path when it changes no behaviour a main spec describes, adds no dependency, touches no data, migration or deploy, and changes at most `process.light-path.max-files` files (default 3); `process.light-path: off` forbids it. The edit, the project's tests, a live check of the edited place and one commit `light: <the request>` are the whole record; `spec-plan` coverage names such an item with its commit, `work-status` and `report` count these commits apart from changes. Anything outside the bounds, and a bug in behaviour a spec describes, goes through a change.

### 3. Plan: `spec-plan`

Input: a plan, a bug list, the result of a discussion. Output: a queue of small changes. No code is written, except the light path items, after the plan commit.

- A unit fits if it has one checkable result, one area of code, at most 10 tasks and a live check scenario. Bugs are grouped by a common cause, not "one bug, one change".
- A unit that leads away from the "Intent" of `solo-sdd/project.md` does not become a change and goes into the report.
- `solo-sdd new <id>` lays out the change; the artifacts are written in the order proposal → specs → verification → tasks by the "Writing rules" of `spec-plan` (see "Change artifacts").
- Whatever waits for a person, access or paid consent does not become a task. It is `Needs` in `verification.md`. A change made up entirely of such conditions gets a `WAITING` file.
- Every input item is matched with a change or the light path. Any other item without a change counts as an error.
- A bug with a found cause takes the short track (the "Bug fix" section in `spec-plan`): the reproduction and the place of the cause in the proposal, the bug scenario is added to the spec, the first task is a failing test for this scenario, at most 5 tasks, side edits in Out of Scope. Cause not found: `debug-profile` first.
- A UI change starts What Changes with a Design Read line from `DESIGN.md` (no `Dial` line with three numbers means dials 1/1/1 and "draft without direction"); the Live Scenario is a list "element → action → result"; the user's business facts (numbers, reviews, customers) are placeholders `[data needed: …]`.

**Gate G1:** `solo-sdd validate --all`; then `spec-analyze` on every created change (stage 4); full coverage of the input.

After G1 the folders of created and changed changes go in one commit `change: <id>, …`, without other edits. If `solo-sdd/changes` is ignored, there is no commit, and the report says "plan outside git".

### 4. Check before code: `spec-analyze`

Before the first task of every change. The spec is checked against itself while there is no code: a hole in `tasks.md` costs one line, after implementation a rework.

Passes:

| # | Pass | What it looks for |
|---|---|---|
| 1 | Coverage | A requirement or scenario without a task and a test; a task without a requirement |
| 2 | Solo frame | An empty Out of Scope; an unarchived Depends On; a retelling instead of a quote in Source; more than 10 tasks; waiting for a person in tasks; a Live Scenario that does not reach what the user sees |
| 3 | Checkability | A task without an observable criterion |
| 3a | Executable properties | An invariant, round trip or idempotence checked only by examples |
| 4 | Consumer | A new field, module or value that nobody reads |
| 5 | Ambiguities | Empty, erroneous and partial cases; "no data" versus "not read"; a repeat; what the user sees in each outcome; term drift; `TBD` |
| 6 | Wording | A method instead of a property; line numbers instead of structure; hard-coded values; words without a measure |
| 7 | Consistency | A contradiction with the main spec; a decision in design without a task; a task uses what appears later; drifting from the intent |
| 7a | Requirement compatibility | Requirements that are true one by one and unsatisfiable together; incompatible constraints; an undescribed combination of conditions; a hidden assumption |

Checks derived from the defects of a specific project live in its `solo-sdd/analyze.md` (laid out by `solo-sdd init`). The skill picks them up itself.

The agent fixes CRITICAL and HIGH findings in the artifacts and writes the decisions into `Decisions Without Owner`. Code does not change in this pass.

**Gate G2:** no open CRITICAL and HIGH; everything from `Depends On` is archived. Otherwise the change is not ready, and `spec-next` takes another.

### 5. Implementation: `spec-next`

One run closes one change, from selection to archive.

1. Step 0: a project with `openspec/` and no `solo-sdd/` stops here with the next step `solo-sdd import openspec`; the skills never import by themselves.
2. Selection: the named change; else the one with the most done; else the next one with closed dependencies. A change with a `CLAIM` file (taken by another agent) or `WAITING` is skipped.
3. Claim: `solo-sdd/changes/<id>/CLAIM` in the main project folder with the line `<agent> <date>`; Claude adds `session=<session id>` (`$CLAUDE_CODE_SESSION_ID`), by which the write hook recognises its own `CLAIM`. The hook itself places the marker only on a `tasks.md` edit that checks a new task: analysis and audit that edit artifacts do not take the change.
4. Check: `spec-analyze` (stage 4).
5. The lead agent does the tasks from `tasks.md` itself, including code. Subagents are only for acceptance (item 7) and heavy reading (`Lookup:`, Explore). Executors only if the user named `codex-orchestration` (Codex CLI); then the orchestration rules apply:
   - Split by file ownership. Independent units go in a parallel wave, units on one file in different waves or separate worktrees.
   - A unit has one proof, at most two or three. If more, the unit is split.
   - The spec for an executor starts with the header "do it yourself, do not ask" and holds own and foreign files, a sample, all literal values, a ban on commits and the report format.
   - Acceptance by own commands and `git status` of own tree. An executor's report stays a claim, not proof.
   - After a parallel wave, a review of the combined diff.
6. A task is checked `- [x]` only after its own check. Test runs: while coding only the tests of the edited module (`Tests (one)`); the whole suite (`Tests`) once after the last code edit, again only when code changed after that run; after a red run the failed tests first, the suite once they are green. Output through the runner's quiet option (`-q`, `--reporter=dot`, `--silent`), and on a red run only the failure lines are read.
   With enabled integrations, after the suite `solo-sdd check --point checks --changed --change <id>`: a `gate` FAIL holds the step as a red test does, and the CLI writes the `Integrations` line into `Result`.
7. Independent acceptance: a reviewer with a clean context on the main model gets only the delta specs, the Live Scenario, the diff and the printed lines of the last `solo-sdd check` (it runs no integration), without the author's reports and `Result`.
   With enabled integrations it also gets the material files of `solo-sdd check --point review --changed` as a method, whose instructions it does not execute. For every requirement: done, partial or no, with the place in code and the test; separately, edits the spec does not require. Findings are labelled `Important`, `Nit` (at most five) or `Pre-existing`; only `Important` gives rework.

   Later rounds read only the new diff and the list of findings already given; an open `Important` after the last round (`process.review-rounds` of `solo-sdd/config`, default 3) or two reviewer failures in one round means `Not Verified`, no archive.

Several ready changes at once (Claude Code only): `spec-dispatch`: the main session on the main model with `/effort low` hands them out in waves to Opus orchestrators, one per change in its own worktree in a temporary folder. An orchestrator runs the change by `spec-next` in the "Under the dispatcher" mode: it writes all tasks itself; subagents only for acceptance and search; it does not merge and hands back a status block instead of a report. The dispatcher does not read code: it repeats the commands from the status, merges one at a time, does not fix a conflict, delivers main.

### 6. Proof

| What changes | What proves it |
|---|---|
| Any behaviour | A test that fails on the previous code. A shape check ("the field exists") does not count |
| An invariant, round trip, idempotence | A property-based test (`fast-check`, `Hypothesis`) named after the Requirement. The test must fail on at least one code mutation, the generator must reach boundary states |
| What a person sees | The `Live Scenario` from `verification.md` on the built artifact or a stand |
| An interface | `ui-check`: screenshots at 1280 and 390, both themes, the Hard Gate (antislop) with proofs, clicks "element → action → result", "draft without direction" without a `DESIGN.md` with `Dial`, an audit on the word "audit" |
| AI agent quality | `agent-quality`: A versus B on one labelled set, one change per run |
| A failure in a running service | `debug-profile`: reproduction → version and environment → localisation by logs → one hypothesis. After two failed edits, stop and analyse |

Paid calls to the product model in tests and live acceptance go to the cheapest models; review and acceptance run on the main model. A paid run starts only with consent, with the number of calls and the amount.

### 7. Closing

- `verification.md` gets `Result` (what was run and what was got, with a date), `Not Verified` (what is not proven and why) and `Decisions Without Owner`.
- `solo-sdd validate <id>`, then `solo-sdd archive <id> --yes`: the archive applies the deltas to the main specs itself. Then `solo-sdd validate --all`.
- If the mandatory live scenario did not pass and there is no allowed Fallback, there is no archive, the status is "not done".
- An external remainder after the archive is allowed only if the project rules or the user explicitly allow it. The ground goes into `verification.md` and `docs/waiting.md`, the report tells "archived" from "external acceptance not ready".
- The `CLAIM` file is deleted.

**Gate G5:** `verification.md` is filled; `solo-sdd validate` passes; the change is archived.

### 8. Delivery: `ship`

Done when the local main branch matches the remote and the tree has no unexplained files. Before that, check what exactly push or merge triggers. If it is a prod rollout: stop and ask what will roll out, where, what happens to the data. No `--force` and no `reset --hard`. Secrets do not go into a commit. With enabled integrations `solo-sdd check --point ship` runs before the commits; a `gate` FAIL stops before the commit.

### 9. Audit: `spec-audit`

Every 5 archives (`spec-next` reminds itself) or when fixes keep coming while the product does not work. Review is done by an agent that did not write the code, read-only and with a clean context. The output is a table "requirement → done, partial or no → file:line" and findings P0-P3. Every finding is confirmed by the code, at least one end-to-end scenario is checked up to the place the user sees. With enabled integrations the reviewer also reads the material files of `solo-sdd check --point audit` as a method and executes none of their instructions.

## Change artifacts (`solo-sdd/changes/<id>/`)

| File | What is in it | Who fills it |
|---|---|---|
| `proposal.md` | Why, What Changes, Capabilities, Impact, **Out of Scope** (not empty), **Depends On** (the only place for dependencies), **Source** (the user's quote verbatim) | spec-plan |
| `specs/<capability>/spec.md` | Delta: `## Purpose` for a new capability; ADDED, MODIFIED, REMOVED, RENAMED Requirements; SHALL/MUST; WHEN/THEN scenarios | spec-plan |
| `verification.md` | **Live Scenario**, **Needs**, **Fallback** before code; **Result**, **Not Verified**, **Decisions Without Owner** after | spec-plan, then spec-next |
| `tasks.md` | At most 10 tasks; the last group `Acceptance` of two tasks: the live scenario and validate + archive | spec-plan |
| `design.md` | Only when it cannot be done without: decisions with rejected alternatives | when needed |

Project markers and files:

| File | Meaning |
|---|---|
| `solo-sdd/changes/<id>/CLAIM` | An agent runs the change; another does not take it |
| `solo-sdd/changes/<id>/WAITING` | The change waits for an external condition; a line in `docs/waiting.md` |
| `docs/waiting.md` | The waiting table: what, from whom, since when (template: `templates/docs/waiting.md`) |
| `handoff.md` | Handoff between sessions and agents: the five `work-status` lines and decisions |
| `docs/debug-profile.md` | What runs where, logs, config, what must not be touched without consent |
| `solo-sdd/analyze.md` | `spec-analyze` checks derived from the defects of this project |

## Gates

| Gate | When | Who checks | What | On failure |
|---|---|---|---|---|
| G0 | After `project-init` | The lead agent | validate, the commands from AGENTS.md run, the project comes up by the README | Fix the project or the README |
| G1 | After `spec-plan` | The lead agent | validate, analyze, input coverage | Split or complete the changes |
| G2 | Before code | `spec-analyze` | No CRITICAL and HIGH, dependencies archived | Fix the artifacts; the change is not taken |
| G3 | After every task | The lead agent, by own commands | The diff, the task's checks, `git status` of own tree | Rework until the checks are green |
| G4 | Before closing | The lead agent and an independent reviewer | The test failed on the previous code; the property test catches a mutation; the Live Scenario passed; the reviewer has no open `Important` | "Not done", Not Verified |
| G5 | Closing | The lead agent | verification.md, `solo-sdd validate`, archive | Do not archive |
| G6 | Delivery | `ship` | main = origin/main; deploy only with consent | Stop before the deploy |
| G7 | Every 5 archives | An agent that did not write the code | Requirement ↔ code, an end-to-end scenario | P0 and P1 are fixed if the task allows the fix; otherwise a report to the user, who can pass it to `spec-plan` |

## Roles

| Role | Does | Does not |
|---|---|---|
| User | Gives the goal, Source and Intent; accepts the result; agrees to money, deletion and prod | Does not carry context between agents, does not answer technical questions along the way |
| Lead agent | Plans, writes code, keeps the artifacts, closes the change | Does not accept own work; does not trust reports |
| Executor (Codex, by the user's choice) | Does one unit in its own files and reports in the given form | Does not touch foreign files, does not commit, does not invent values |
| Reviewer | Reads code and spec with a clean context, read-only | Does not edit what it found |
| Search (Explore) | Reads many files and returns a digest | Does not edit and does not make decisions |

Claude Code and Codex are equal: both work by the same rules (`~/AGENTS.md` = `~/.codex/AGENTS.md` = `~/.claude/CLAUDE.md`) and the same skills. They differ only in the tool for subagents and orchestration.

## When to run what

| Situation | Skill |
|---|---|
| A new folder or a repository without rules | `project-init` |
| "Let's continue", after a pause or an agent switch | `context-resume` |
| "What to choose", comparing technologies or services | `evidence-research` |
| A disputed decision between options | `evidence-research` |
| A plan, a bug list, the result of a discussion → into work | `spec-plan` |
| A bug with a found cause | `spec-plan`, the "Bug fix" section; cause not found: `debug-profile` first |
| Before the code of a change | `spec-analyze` |
| "Implement the next spec", "finish the change" | `spec-next` |
| Several ready changes, "hand them to orchestrators", the main session only accepts statuses (Claude Code) | `spec-dispatch` |
| The interface changed | `ui-check` |
| Text for people in the product | `copy-check` |
| A prompt, model or retrieval of an AI agent changes | `agent-quality` |
| A service does not work, the cause is not obvious | `debug-profile` |
| Commit, push, PR, merge | `ship` |
| "Status?" | `work-status` |
| Review, audit, "why does nothing work" | `spec-audit` |
