---
name: spec-next
description: Use when the user asks to implement, continue or close a change or spec - "implement the next spec", "take the next spec", "pick an unclosed spec", "finish the spec to the end", "close out the change", "finish the spec", "if done, archive", "use opus sonnet orchestration and /spec-next", "find a spec nobody has taken and implement it" - or names a change to finish. Also use when about to report a change as done.
---

# spec-next: one change from selection to archive

One run closes one change completely. "Done" means: the change is archived, the specs are synced, everything is checked live. Green tests without an archive are "not done". An archive with an allowed external remainder does not mean completed external acceptance.

Argument (optional): the name or number of a change. Without an argument, choose yourself.

## Order

0. **Legacy tree.** The project has `openspec/` and no `solo-sdd/`: stop before any change work, change no file and name the next step `solo-sdd import openspec`; do not import by yourself.
1. **Project rules.** Read `AGENTS.md` (and `CLAUDE.md`, if there is one). If they diverge from this skill, the project rules apply.
2. **Selection.** `solo-sdd list --json`. Take the named change; else the one with the most tasks done; else the next one in order with closed dependencies. Skip a change whose folder has a `CLAIM` from another agent or `WAITING` (waits for an external condition, see `docs/waiting.md`), and a change whose proposal `Depends On` section names changes not archived yet.
3. **Claim.** Create `CLAIM` in the main project folder, even if the implementation goes into a worktree. Claude: `echo "claude $(date +%F) session=$CLAUDE_CODE_SESSION_ID" > solo-sdd/changes/<id>/CLAIM`: by the session id the write hook tells its own `CLAIM` from another's (without the id it adds it itself on the first edit). Codex: the line `codex <date>`.
4. **Context.** Read `proposal.md`, `design.md`, `tasks.md`, the delta specs.
4a. **Check before code.** The `spec-analyze` skill on this change. Fix CRITICAL and HIGH findings in the artifacts before the first code edit. An unarchived dependency from `Depends On` means the change is not ready: remove `CLAIM` and go back to step 2.
5. **Implementation.** You do all items of `tasks.md` yourself, including code: you hold the plan, a handoff to a subagent loses precision. Subagents are only for independent acceptance (step 7a, tag `Review:`) and heavy reading (tag `Lookup:`, only `subagent_type: Explore`, the model set explicitly and not expensive).

   The exception: the user named Codex; then executors write the code by the skill `codex-orchestration`, and you lay out the tasks and accept the result with your own commands. A request to have one model plan and another write the code is not an exception: you write the code yourself. The same in Codex: its own subagents only for acceptance and search. Check `- [x]` only after checking the item.

   Code that makes an existing test fail is fixed, not the test: an assertion changes or goes only by a task that names a MODIFIED or REMOVED requirement; a change of a test's setup, cost or layout keeps every assertion.
6. **Checks** from `AGENTS.md` and from `tasks.md`.
   - Test runs: while coding only the tests of the edited module run (`Tests (one)`); the whole suite (`Tests`) runs once after the last code edit and again only when code changed after that run; after a red run the failed tests first, the suite once they are green.
   - Output through the runner's quiet option (`-q` for pytest, `--reporter=dot` for vitest, `--silent` for jest; unittest prints only dots by default); on a red run read only the failure lines, not the whole log.
   - A Nit fixed in code takes the tests of its module and one more suite run after the last such edit, without a new review round; a finding closed without a code edit takes no run. Under the dispatcher the dispatcher's run after merge stays as it is and is not counted.
   - Integrations: when `solo-sdd config get integrations` is not empty, after the `Tests` run `solo-sdd check --point checks --changed --change <id>`. Code 1 (a `gate` FAIL) holds the step as a red test does: fix, then run the call again; an `advice` FAIL does not hold it. The CLI writes the `Integrations checks (tree <hash>): …` line into `## Result` of `verification.md`: when you fill `## Result`, keep the `Integrations` lines (a repeated call restores them).
7. **Live test** of the affected scenario on real input or a stand. Paid calls to the product model in it go to the cheapest product model and with the user's consent.
7a. **Independent acceptance.** Read `acceptance.md` each time this step starts, also after compaction: a `Review:` reviewer who did not write the code, what it gets and does not get, its task, the finding labels and the rounds; an open `Important` blocks the archive.
8. **Blockers.** Items that wait for external access or a person's decision: into `verification.md` (the "Not Verified" section) and a line in `docs/waiting.md`. A new change only for work beyond the specification's boundaries. If the project rules require otherwise, they apply.
9. **Closing.** Read `closing.md` each time this step starts, also after compaction: no archive without the mandatory tasks, the live scenario and closed `Important` findings; then `solo-sdd validate <id>`, `solo-sdd archive <id> --yes` and `solo-sdd validate --all`.
10. **Delivery.** Delete `CLAIM`. Go through `/ship` up to a merged main branch, unless the project rules explicitly forbid it. The exception: push or merge triggers a prod deploy (`/ship`, the "Deploy" step): stop before this action and ask, naming what rolls out and where.
11. **Stop.** Do not start the next change.

## Under the dispatcher

The mode turns on when the prompt names "Under the dispatcher" and passes `MAIN`, `WORKTREE` and `BRANCH` (this is how `spec-dispatch` launches orchestrators). The order is the same, with differences:

- Skip step 0: the dispatcher did it for the project. Step 2: the change is named in the prompt.
- Step 3: `CLAIM` goes into `<MAIN>/solo-sdd/changes/<id>/CLAIM`.
- The prompt has the line "Remove from Depends On: <names>": as the first edit, before step 4a, remove these names from `Depends On` of your `proposal.md` in `WORKTREE` (an empty section becomes `none`); they are not dependencies, do not write into `MAIN`.
- Step 4a: an unarchived dependency: do not choose another change: remove `CLAIM` and hand back `STATUS: not_ready` with the dependency in `NOTES`.
- All code, artifacts, `solo-sdd archive` and commits go in `WORKTREE` (`cd <WORKTREE> && …` or absolute paths). The reviewer and search get the absolute path of `WORKTREE` and a ban on writing outside it.
- Do not prepare the environment: the dispatcher has already copied into `WORKTREE` the git-ignored `solo-sdd/`, `AGENTS.md`, the paths of the "Working copy" section and individually ignored project documents, and linked `node_modules` and `.venv`. Something is missing: `STATUS: blocked` with what is missing. Only `CLAIM` is written into the main folder: edit `AGENTS.md`, documents and specs, even git-ignored ones, in `WORKTREE`; the dispatcher carries them over after merge. Do not delete or commit the dependency links.
- Step 5. The orchestrator does all tasks of the change itself, whatever their number and the number of code areas. Subagents are only `Review:` (step 7a, without `model`, a clean context) and `Lookup:` (`subagent_type: Explore`). A subagent description starts with the role tag; the hook rejects your other subagents.
- The reviewer and search run in the foreground: `Agent` without `run_in_background`, independent ones in one message. The turn does not end while your subagent or your background command is running; the status comes when all have returned, including after rework from the review and its repeated acceptance.
- Put a rule into the subagent prompt: a long-lived process (a server etc.) only as a managed background task, stopped before the report; a temporary folder is created and removed by the stand itself; whatever could not be cleaned up (for example, the environment forbids deleting in the system TMP) is named in the report with the process, port or folder.

  A subagent left a running process: send it back through `SendMessage`: it stops its task by id; if that fails, it is a leftover. Before the status stop your background tasks by id; list the processes, ports and folders left after your commands, and everything the subagents named, as a separate line `Leftovers: <process, port or folder>` right under `NOTES`; it goes above the `NOTES` line limit. No leftovers, no line.
- The status field `LIVE` is one command that runs from the `WORKTREE` root without manual steps, without files outside `WORKTREE` and without preparation known only to the orchestrator, and gives the same output as stated in the status. It is copied from a code span of a step of the change's `## Live Scenario` in `verification.md`: `sdd-dispatch.py accept` refuses any other command without running it, so a stand call is written into that section as a code span.

  No `&&`, `||`, `;`, pipe `|` and no leading `cd `: the handback hook rejects `archived`; a pipe is a second command, and there is no need to shorten or filter the stand output: the dispatcher does that.

  A Live Scenario of several steps, with fixtures (including those described only in prose of `verification.md`, which the dispatcher does not run) or a walk through an application window: write a stand: a script in the repository that prepares and removes its data itself (for a window, opens the window and prints the summary of the checks), and put its call into `LIVE`.
- Step 10: do not merge into the main branch and do not run `/ship`. Commit everything into `BRANCH`, then delete `<MAIN>/solo-sdd/changes/<id>/CLAIM`. The dispatcher does the delivery.
- Step 11: do not start the next change.
- Instead of the report, as the last message hand back only the status block in the format from the dispatcher prompt (capability `orchestrator-status`); the number of rounds, whether the extra round ran, `Pre-existing` and a reviewer failure go into the findings line of the `REVIEW` field. The report's `Lesson` lines (global rules, section Lessons) go right under `NOTES`, above its line limit; no lesson, no line.

  The change did not reach the archive (the live scenario failed, a blocker, an open `Important`): `STATUS: not_ready` or `blocked`, the reason in `NOTES`. The handback hook rejects `archived` if the commit, the archive or the removed `CLAIM` do not match the fields: remove the mismatch or hand back `not_ready`.

## Decisions without questions

Decide yourself and record the decision in the report. The only allowed question is before paid requests, deleting data or an action on prod: name the number of requests and the amount.

| Thought | What to do |
|---|---|
| "The tests are green, so it is done" | Not done until there is a live test and an archive |
| "I checked everything myself, no reviewer needed" | Own work is not accepted by its author: step 7a |
| "No key or access, I will wait" | Look for a workaround: mocks, old project data, `.env`, a neighbouring service. Not found: a blocker in `verification.md` ("Not Verified") and `docs/waiting.md`, close the rest |
| "I will ask which option to choose" | Choose a reasoned one, record it in the report |
| "I will archive, the live test later" | The test first |
| "I will start the next change too" | No. Another agent may be running it |
| "The validation error is expected" | Fix the call or the artifact |
| "The user will commit and merge themselves" | Delivery is part of closing, go through `/ship` |
| "The subagent works in the background, I will hand back the status, it will catch up" | No, wait for it |
| "One more review round, maybe it finds something" | At most `process.review-rounds` rounds (default 5), plus one extra round only after the second or later round when every open `Important` lies only in the lines of the last rework; after that with an open `Important`: "not done" |

## Report (in the user's language, in this form)

```
Change: <id>
Status: closed and archived | archived, external acceptance not ready — <ground and remainder> | not done, not archived — <what is missing>
Checks: <command — result>
Suite: <before> (<change>) -> <after> | n/a -> <after>
Live test: <what was run, what was got> | not done — <reason>
Independent acceptance: rounds <k>; extra round: ran | did not run; done <n> of <m>; findings: <Important and Pre-existing as a list, Nit as a count>; reviewer failure: <round and what was not got> | no remarks
Decisions made without you: <list>
Moved to a new change: <id> | none
Lesson: <line written or refined in ## Lessons> -> <path of that AGENTS.md>, one line each | none
<extra lines, only when there are such lessons: Lesson for solo-sdd: <sentence> · Lesson (no AGENTS.md): <sentence> · Lesson (not written): <sentence>>
Not checked live: <what and why, recorded in verification.md and docs/waiting.md> | everything checked
Delivery: <commit, PR, whether merged> | waits for deploy consent: <what and where> | forbidden by the project rules
Needs from you: <action> | nothing
```

If the number of folders in `solo-sdd/changes/archive` after this archive is a multiple of 5, add the line: `Time for: /spec-audit on the main specs`.
