# Skills audit

Every skill of `targets.json` and each of its steps: `gate (code)` (a condition a hook or the CLI already holds), `gate (text)` (a condition only the text holds; `hook: yes` when a hook or the CLI could hold it) or `method` (how to think and in what order). A step is a top-level `N.`, `Na.` or `**N.` item of `SKILL.md` outside fenced code, up to the next item or heading, with its step files; a skill without items has one `whole text` row. `python3 tests/stands/skill-ablation.py audit` and `tests/test_skill_commands.py` keep the table in step with the skills.

A skill with a task set under `tests/stands/skill-ablation/` is measured by `tests/stands/skill-ablation.py` (`docs/release.md`, "Skill measurement"): each run goes under the skill's step table as `### Run <date> <model>` with the `grade` output. A skill whose last two runs with a compared task each have full passes no more than none passes carries the line `candidate to cut: the owner decides`; only the owner removes that line or the skill.

## agent-quality

| Heading | Step | Mark | Hook | Why |
|---|---|---|---|---|
| Order | 1. Version | method |  |  |
| Order | 2. Case set | method |  |  |
| Order | 3. What counts as an answer | method |  |  |
| Order | 4. Metrics | method |  |  |
| Order | 5. Baseline | gate (text) | hook: no | a baseline run before any comparison leaves no tool event a hook could read |
| Order | 6. Cost before the run | gate (text) | hook: no | the amount is said in chat; the model guard covers only the model of a Bash test |
| Order | 7. Change and a repeated run | method |  |  |
| Order | 8. Live check | method |  |  |

## blockers

| Heading | Step | Mark | Hook | Why |
|---|---|---|---|---|
| Order | 1. List | method |  |  |
| Order | 2. Split | method |  |  |
| Order | 3. A project with a solo-sdd/ tree | gate (code) |  | `solo-sdd new` refuses an id that is not kebab-case or already taken |
| Order | 4. A project without a solo-sdd/ tree | method |  |  |
| Order | 5. Commit | gate (code) |  | the `stop` hook returns the agent on uncommitted edits of the session |
| Order | 6. Continuing | method |  |  |

## changes

| Heading | Step | Mark | Hook | Why |
|---|---|---|---|---|
| Order | 1. solo-sdd list --json and the folder | method |  |  |
| Order | 2. For every change | method |  |  |
| Order | 3. A table in number order | method |  |  |
| Order | 4. Under the table, groups | method |  |  |

## codex-orchestration

| Heading | Step | Mark | Hook | Why |
|---|---|---|---|---|
|  | whole text | method |  |  |

## context-resume

| Heading | Step | Mark | Hook | Why |
|---|---|---|---|---|
| Order | 1. Project rules | gate (code) |  | the `context` hook puts AGENTS.md, project.md and docs/status.md into the session |
| Order | 2. Handoff | method |  |  |
| Order | 3. Current state | method |  |  |
| Order | 4. History | method |  |  |
| Order | 5. Check | method |  |  |
| Order | 6. Map | method |  |  |

## copy-check

| Heading | Step | Mark | Hook | Why |
|---|---|---|---|---|
| Loop | 1. Source | method |  |  |
| Loop | 2. Draft | method |  |  |
| Loop | 3. Audit | method |  |  |
| Loop | 4. Final | gate (text) | hook: yes | a Write check of the changed text files for a long dash and ` -- ` between words |
| Loop | 5. Write | method |  |  |

## debug-profile

| Heading | Step | Mark | Hook | Why |
|---|---|---|---|---|
| 2. Diagnosis | 1. Reproduction | method |  |  |
| 2. Diagnosis | 2. Version and environment | method |  |  |
| 2. Diagnosis | 3. Input data | method |  |  |
| 2. Diagnosis | 4. Localisation | method |  |  |
| 2. Diagnosis | 5. Hypothesis | method |  |  |
| 2. Diagnosis | 6. Fix | gate (text) | hook: no | whether an edit is the fix of the diagnosed cause is a judgement |
| 3. A bug in code | 1. Reproduction | gate (text) | hook: no | a hook cannot tell the failing test of this bug from another test |
| 3. A bug in code | 2. Trace back | method |  |  |
| 3. A bug in code | 3. Comparison | method |  |  |
| 3. A bug in code | 4. One hypothesis | method |  |  |
| 3. A bug in code | 5. Fix | gate (text) | hook: no | the route through the bug fix section is a judgement of what was found |

### Run 2026-11-22 claude-opus-5-5

```text
skill: debug-profile; run: skill-ablation-debug-profile-uxgm21_w
models: claude-opus-5-5
| task | variant | outcome | path | tokens | note |
|---|---|---|---|---|---|
| dp-code | full | pass | 2 of 2 | 82817 |  |
| dp-code | cut | pass | 2 of 2 | 82550 |  |
| dp-code | none | pass | 2 of 2 | 80893 |  |
| dp-service | full | fail | 1 of 2 | 83255 |  |
| dp-service | cut | fail | 1 of 2 | 82343 |  |
| dp-service | none | fail | 1 of 2 | 80907 |  |
compare: full 1 of 2, cut 1 of 2, none 1 of 2
not run: 0; leaked: 0; unreadable: 0; not made: 0
```

The `dp-service` rows of this run had no `logs/` in the work folder: the fixture's `logs/*.log` are ignored by the `*.log` line of `.gitignore` and were never committed. The run below repeats `dp-service` with the three logs restored in the working folder.

### Run 2026-11-22 claude-opus-5-5

```text
skill: debug-profile; run: skill-ablation-debug-profile-7zqkopy3
models: claude-opus-5-5
| task | variant | outcome | path | tokens | note |
|---|---|---|---|---|---|
| dp-code | full | not run | - | - |  |
| dp-code | cut | not run | - | - |  |
| dp-code | none | not run | - | - |  |
| dp-service | full | pass | 2 of 2 | 82653 |  |
| dp-service | cut | fail | 1 of 2 | 81806 |  |
| dp-service | none | fail | 1 of 2 | 81372 |  |
compare: full 1 of 1, cut 0 of 1, none 0 of 1
not run: 3; leaked: 0; unreadable: 0; not made: 0
```

## evidence-research

| Heading | Step | Mark | Hook | Why |
|---|---|---|---|---|
| Order | 1. Criteria | method |  |  |
| Order | 2. Search | method |  |  |
| Order | 3. Specifics | method |  |  |
| Order | 4. Freshness | method |  |  |
| Order | 5. Filtering | method |  |  |
| Order | 6. Comparison | method |  |  |
| Order | 7. Recommendation | method |  |  |
| Order | 8. Unknowns | method |  |  |
| Order | 9. Outside check | gate (text) | hook: yes | the `stop` hook could return a final answer with a source table when no `Check:` subagent ran |

### Run 2026-11-22 claude-opus-5-5

```text
skill: evidence-research; run: skill-ablation-evidence-research-s6_mqkm7
models: claude-opus-5-5
| task | variant | outcome | path | tokens | note |
|---|---|---|---|---|---|
| er-alive | full | pass | 2 of 2 | 84838 |  |
| er-alive | cut | pass | 2 of 2 | 84834 |  |
| er-alive | none | fail | 0 of 2 | 80342 |  |
| er-hosting | full | pass | 2 of 2 | 87170 |  |
| er-hosting | cut | fail | 0 of 2 | 87144 |  |
| er-hosting | none | pass | 2 of 2 | 80801 |  |
compare: full 2 of 2, cut 1 of 2, none 1 of 2
not run: 0; leaked: 0; unreadable: 0; not made: 0
```

## health

| Heading | Step | Mark | Hook | Why |
|---|---|---|---|---|
| What to check | 1. Project description | method |  |  |
| What to check | 2. Otherwise find them yourself | method |  |  |
| What to check | 3. The cheapest check for each | method |  |  |
| What to check | 4. Local processes | method |  |  |
| What to check | 5. The provider is down | method |  |  |

## next-up

| Heading | Step | Mark | Hook | Why |
|---|---|---|---|---|
| Order | 1. Sources | gate (text) | hook: no | an unread source named in the `Unread:` line is read from the report, not from a tool event |
| Order | 2. Evidence | gate (text) | hook: no | whether an output or a log line meets a row's condition is a judgement |
| Order | 3. Closing | gate (text) | hook: yes | a write hook could refuse an edit of `docs/waiting.md` that drops a first-table row not found under `## Closed` |
| Order | 4. WAITING files | method |  |  |
| Order | 5. Queue | method |  |  |
| Order | 6. Stop | gate (text) | hook: no | a change started after the report is the owner's next request, not a tool event of this run |

## plan-input

| Heading | Step | Mark | Hook | Why |
|---|---|---|---|---|
| Order | 1. Target | method |  |  |
| Order | 2. Process tree | gate (text) | hook: no | whether the target the owner names has git and a `solo-sdd/` tree is read from that folder before any write; no tool event marks it |
| Order | 3. Sections | method |  |  |
| Order | 4. Done or planned | method |  |  |
| Order | 5. Checks of a decided item | gate (text) | hook: no | a failed check is read from the commands' answers by judgement, not from one tool event |
| Order | 6. Each letter section | method |  |  |
| Order | 7. Slicing hint | method |  |  |
| Order | 8. Nothing to plan | gate (text) | hook: no | whether any item is left to plan is a judgement on the sections |
| Order | 9. Save | gate (text) | hook: yes | a write hook could refuse writing an input file inside a git repository or over an existing file |
| Order | 10. Launch lines | gate (text) | hook: no | the lines stand in the file and the reply, a hook sees no reply text |

## project-init

| Heading | Step | Mark | Hook | Why |
|---|---|---|---|---|
| Order | 1. Mode | method |  |  |
| Order | 2. Git | gate (code) |  | `solo-sdd ignore --write` writes the block and refuses process paths |
| Order | 3. Process tree | gate (code) |  | `solo-sdd init` lays out the tree and refuses a second tree next to `openspec/` |
| Order | 4. .env.example | gate (text) | hook: no | the guard already refuses overwriting `.env`; the empty fields are a judgement |
| Order | 4a. Codebase map | method |  |  |
| Order | 5. AGENTS.md | method |  |  |
| Order | 5a. DESIGN.md | method |  |  |
| Order | 6. CLAUDE.md | gate (text) | hook: yes | a `stop` check for a project with AGENTS.md whose CLAUDE.md has no `@AGENTS.md` line |
| Order | 7. Check | gate (code) |  | `solo-sdd validate --all` exits not 0 on a broken tree |
| Order | 7a. Artifact commit | gate (text) | hook: no | which paths a commit takes depends on what the run changed |
| Order | 8. README | gate (text) | hook: no | a run of the README in a clean shell is a judgement of what it proves |

## relay

| Heading | Step | Mark | Hook | Why |
|---|---|---|---|---|
| Order | 1. Context | gate (code) |  | the CLAIM guard refuses edits of a change another session holds |
| Order | 2. Parsing | method |  |  |
| Order | 3. Done | method |  |  |
| Order | 4. Not checked, did not help, failed | method |  |  |
| Order | 5. Needs from the user | method |  |  |
| Order | 6. Found outside the change | method |  |  |
| Order | 7. Delivery | gate (code) |  | the `stop` hook returns the agent on uncommitted edits and an unmerged PR |

## report

| Heading | Step | Mark | Hook | Why |
|---|---|---|---|---|
| Form (in the user's language, as plain text) | 1. Result | method |  |  |
| Form (in the user's language, as plain text) | 2. What was done | method |  |  |
| Form (in the user's language, as plain text) | 3. Numbers | gate (text) | hook: no | a number's source and status are read from the text, not from a tool event |
| Form (in the user's language, as plain text) | 4. What is broken or at risk | method |  |  |
| Form (in the user's language, as plain text) | 5. What waits | method |  |  |
| Form (in the user's language, as plain text) | 6. What next | method |  |  |

## review-principles

| Heading | Step | Mark | Hook | Why |
|---|---|---|---|---|
| Order | 1. Owner login | gate (text) | hook: no | whose remark counts is read from the answers of `gh`, not from a tool event a hook sees |
| Order | 2. Sources | gate (text) | hook: no | an unread source named in the `Unread:` line is read from the report |
| Order | 3. Remarks | method |  |  |
| Order | 4. Rules and patterns | method |  |  |
| Order | 5. REVIEW.md | gate (text) | hook: yes | a write hook could refuse a `REVIEW.md` edit that drops a rule line of the file before it |
| Order | 6. Parallel mode | gate (text) | hook: no | whether the held-out file holds a measured change's remark is a judgement on text |
| Order | 7. Stop | method |  |  |

## ship

| Heading | Step | Mark | Hook | Why |
|---|---|---|---|---|
| Order | 1. Repository rules | method |  |  |
| Order | 2. Deploy | gate (text) | hook: no | what a push deploys is read from the project, a hook cannot know it |
| Order | 3. Inventory | gate (code) |  | the `stop` hook returns the agent on uncommitted edits; `solo-sdd check --point ship` holds a gate FAIL |
| Order | 4. Secrets | gate (code) |  | the guard refuses `git add` of `.env` and secret files |
| Order | 5. Commits | method |  |  |
| Order | 6. Push | gate (text) | hook: yes | a Bash guard refusing `git push --force` and `-f` |
| Order | 7. PR | gate (code) |  | the merge guard sends merges through `sdd-pr.py`, whose gates hold |
| Order | 8. Sync | method |  |  |
| Order | 9. Check | gate (text) | hook: no | the agent's own comparison; the open PR gate of `stop` covers part of it |
| Order | 10. Promotion | gate (text) | hook: no | a promotion is printed by `sdd-pr.py`; carrying it into the report is text |

## spec-analyze

| Heading | Step | Mark | Hook | Why |
|---|---|---|---|---|
| What to read | 0. Legacy tree | gate (text) | hook: yes | a write guard refusing change edits in a project with `openspec/` and no `solo-sdd/` |
| What to read | 1. The project rules | method |  |  |
| What to read | 2. The change artifacts | method |  |  |
| What to read | 3. The main specs of the affected | method |  |  |
| What to read | 4. solo-sdd/analyze.md, if the project has it | method |  |  |
| What to read | 5. Code only to check an artifact's | method |  |  |
| Passes | 1. Coverage | method |  |  |
| Passes | 2. The change frame | gate (text) | hook: yes | `solo-sdd validate` could check Out of Scope, archived Depends On and Impact paths as it checks the task count |
| Passes | 3. Checkability | method |  |  |
| Passes | 3a. Executable properties | method |  |  |
| Passes | 4. Consumer | method |  |  |
| Passes | 4a. Trust boundary | method |  |  |
| Passes | 5. Ambiguities | method |  |  |
| Passes | 6. Wording | method |  |  |
| Passes | 7. Consistency | method |  |  |
| Passes | 7a. Requirement compatibility | method |  |  |
| Passes | 1. Put them into a table condition | method |  |  |
| Passes | 2. Compare the rows whose conditions overlap | method |  |  |
| Passes | 3. The fix is as for the | method |  |  |
| Passes | 7b. Overlap with open changes | gate (text) | hook: yes | `solo-sdd validate --all` could report two open changes modifying one requirement without Depends On |

## spec-audit

| Heading | Step | Mark | Hook | Why |
|---|---|---|---|---|
| Order | 1. Scope | method |  |  |
| Order | 2. Baseline | method |  |  |
| Order | 3. Independent reviewer | gate (code) |  | the Agent guard holds the `Review:` model |
| Order | 4. Requirement table | method |  |  |
| Order | 4a. Security pass | gate (code) |  | `solo-sdd check --point audit --tag security` exits not 0 on a refusal |
| Order | 5. Checking findings | method |  |  |
| Order | 6. End-to-end path | method |  |  |
| Order | 7. Report | method |  |  |
| Order | 8. Fixing | gate (text) | hook: no | whether the task allows edits is read from the request |

## spec-dispatch

| Heading | Step | Mark | Hook | Why |
|---|---|---|---|---|
| Order | 0. Preparation | gate (text) | hook: no | the preparation reads settings whose meaning the hook does not know |
| Order | 1. Subagent depth | gate (text) | hook: yes | the Agent guard could refuse an `Orchestrator` launch while the spawn depth is below 2 |
| Order | 2. Pipeline | gate (code) |  | `sdd-dispatch-plan.py` decides what is launched and what waits |
| Order | 3. What to launch | gate (text) | hook: no | the launch line lives in the session; a hook does not see it |
| Order | 4. Launch | gate (code) |  | the worktree guard allows a worktree only under a temporary folder |
| Order | 5. Waiting | method |  |  |
| Order | 6. Status acceptance | gate (code) |  | the handback hook and `sdd-dispatch.py accept` check the status block |
| Order | 7. Merge one at a time | gate (code) |  | `sdd-dispatch.py land-local` and `sdd-pr.py` merge with their gates |
| Order | 8. The pipeline runs | method |  |  |
| Order | 9. Questions to the user | gate (text) | hook: no | which decision needs the user is a judgement; the AskUserQuestion guard holds only the window's language |
| Order | 10. Delivery | gate (code) |  | the `stop` hook returns the agent on uncommitted edits and an unmerged PR |
| Order | 11. Report | method |  |  |

## spec-next

| Heading | Step | Mark | Hook | Why |
|---|---|---|---|---|
| Order | 0. Legacy tree | gate (text) | hook: yes | a write guard refusing change edits in a project with `openspec/` and no `solo-sdd/` |
| Order | 1. Project rules | gate (code) |  | the `context` and `subagent-context` hooks give the session the project rules |
| Order | 2. Selection | gate (code) |  | the CLAIM guard refuses edits of a change with another session's CLAIM or a WAITING file |
| Order | 3. Claim | gate (code) |  | the CLAIM guard writes and checks CLAIM by the session id |
| Order | 4. Context | method |  |  |
| Order | 4a. Check before code | gate (text) | hook: yes | a write guard refusing the first code edit of a change when no `Analyze:` or `Judge:` subagent ran and `process.analyze` is on |
| Order | 5. Implementation | gate (code) |  | the Agent guard allows a subagent only the role tags and their models |
| Order | 6. Checks | gate (text) | hook: no | which run is the module's and which the suite's is read from the project's command table |
| Order | 7. Live test | gate (text) | hook: no | whether a run is the live scenario is a judgement |
| Order | 7a. Independent acceptance | gate (code) |  | the archive guard refuses `solo-sdd archive` without a `Review:` agent after the first code edit |
| Order | 8. Blockers | gate (text) | hook: no | what waits for a person is a judgement |
| Order | 9. Closing | gate (code) |  | `solo-sdd archive` applies the deltas and the archive guard holds the review |
| Order | 10. Delivery | gate (code) |  | the `stop` hook returns the agent on an unarchived ready change, uncommitted edits and an unmerged PR |
| Order | 11. Stop | gate (text) | hook: no | the next change is ordinary work a hook cannot tell from this one |

## spec-plan

| Heading | Step | Mark | Hook | Why |
|---|---|---|---|---|
| Order | 0. Legacy tree | gate (text) | hook: yes | a write guard refusing change edits in a project with `openspec/` and no `solo-sdd/` |
| Order | 1. Context | method |  |  |
| Order | 1a. Light path | method |  |  |
| Order | 2. Units | gate (code) |  | `solo-sdd validate` refuses a change above `process.max-tasks` |
| Order | 2a. Codebase map | method |  |  |
| Order | 3. Order and dependencies | gate (text) | hook: no | `solo-sdd new` holds only the id form; what must be archived earlier is a judgement |
| Order | 4. Check against the intent | method |  |  |
| Order | 5. Creation | method |  |  |
| Order | 6. External conditions | gate (text) | hook: no | what needs a person or a paid call is a judgement |
| Order | 7. Check | gate (code) |  | `solo-sdd validate --all` exits not 0 on an error |
| Order | 7a. Cross-check | gate (text) | hook: yes | a Bash guard refusing the plan commit when no `Analyze:` or `Judge:` subagent ran after the changes were created |
| Order | 8. Coverage | method |  |  |
| Order | 9. Plan commit | gate (text) | hook: no | the plan commit's branch follows from settings the step reads |
| Bug fix | 1. The cause before the change | gate (text) | hook: no | whether a cause is found or guessed is a judgement |
| Bug fix | 2. proposal.md | method |  |  |
| Bug fix | 3. Spec | method |  |  |
| Bug fix | 4. verification.md | method |  |  |
| Bug fix | 5. tasks.md | gate (text) | hook: yes | `solo-sdd validate` could check `process.bugfix-max-tasks` for a change whose name holds `fix` |
| Bug fix | 6. Closing | method |  |  |

## ui-check

| Heading | Step | Mark | Hook | Why |
|---|---|---|---|---|
| Order | 1. Reference | method |  |  |
| Order | 2. Build | method |  |  |
| Order | 3. Screenshots | gate (text) | hook: yes | the `stop` hook checks only that a browser check ran; it could count a screenshot per width of `ui.widths` |
| Order | 4. Check against the reference | method |  |  |
| Order | 5. Clicks | gate (text) | hook: no | a click line is read from the report, not from a tool event |
| Order | 6. Texts | method |  |  |
| Order | 7. Gate | gate (text) | hook: no | the Hard Gate is a judgement on the rules |
| Order | 8. Fix | method |  |  |
| Audit | 1. Read docs/ and take the number | method |  |  |
| Audit | 2. Write docs/ui-audit-NNN-YYYY-MM-DD.md | method |  |  |
| Audit | 3. Every finding has | method |  |  |
| Audit | 4. Until the user answers, no project | gate (text) | hook: no | which file is the audit file is known only to the session |
| Audit | 5. The user named numbers | method |  |  |

## work-status

| Heading | Step | Mark | Hook | Why |
|---|---|---|---|---|
|  | whole text | method |  |  |

## Gates a hook could hold

The `hook: yes` rows above, for the owner to plan as changes.

| Skill | Heading | Step | What a hook or the CLI would hold |
|---|---|---|---|
| `copy-check` | Loop | 4. Final | a Write check of the changed text files for a long dash and ` -- ` between words |
| `evidence-research` | Order | 9. Outside check | the `stop` hook could return a final answer with a source table when no `Check:` subagent ran |
| `next-up` | Order | 3. Closing | a write hook could refuse an edit of `docs/waiting.md` that drops a first-table row not found under `## Closed` |
| `plan-input` | Order | 9. Save | a write hook could refuse writing an input file inside a git repository or over an existing file |
| `project-init` | Order | 6. CLAUDE.md | a `stop` check for a project with AGENTS.md whose CLAUDE.md has no `@AGENTS.md` line |
| `review-principles` | Order | 5. REVIEW.md | a write hook could refuse a `REVIEW.md` edit that drops a rule line of the file before it |
| `ship` | Order | 6. Push | a Bash guard refusing `git push --force` and `-f` |
| `spec-analyze` | What to read | 0. Legacy tree | a write guard refusing change edits in a project with `openspec/` and no `solo-sdd/` |
| `spec-analyze` | Passes | 2. The change frame | `solo-sdd validate` could check Out of Scope, archived Depends On and Impact paths as it checks the task count |
| `spec-analyze` | Passes | 7b. Overlap with open changes | `solo-sdd validate --all` could report two open changes modifying one requirement without Depends On |
| `spec-dispatch` | Order | 1. Subagent depth | the Agent guard could refuse an `Orchestrator` launch while the spawn depth is below 2 |
| `spec-next` | Order | 0. Legacy tree | a write guard refusing change edits in a project with `openspec/` and no `solo-sdd/` |
| `spec-next` | Order | 4a. Check before code | a write guard refusing the first code edit of a change when no `Analyze:` or `Judge:` subagent ran and `process.analyze` is on |
| `spec-plan` | Order | 0. Legacy tree | a write guard refusing change edits in a project with `openspec/` and no `solo-sdd/` |
| `spec-plan` | Order | 7a. Cross-check | a Bash guard refusing the plan commit when no `Analyze:` or `Judge:` subagent ran after the changes were created |
| `spec-plan` | Bug fix | 5. tasks.md | `solo-sdd validate` could check `process.bugfix-max-tasks` for a change whose name holds `fix` |
| `ui-check` | Order | 3. Screenshots | the `stop` hook checks only that a browser check ran; it could count a screenshot per width of `ui.widths` |
