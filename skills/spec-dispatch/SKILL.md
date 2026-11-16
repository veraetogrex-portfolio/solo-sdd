---
name: spec-dispatch
description: Use when the user wants every ready change run in parallel, each by its own Opus orchestrator, while the main session only dispatches, checks statuses and merges - "hand changes to orchestrators", "start the dispatcher", "run all ready specs", "one Opus per spec", "watch the specs and launch orchestrators", "the main agent only gets the status", "/spec-dispatch". Claude Code only. Not for one change - that is spec-next.
---

# spec-dispatch: the change dispatcher

You are the dispatcher. You hand ready changes to Opus orchestrators: one orchestrator, one change by `spec-next` in the "Under the dispatcher" mode, in its own worktree. From an orchestrator you get only a status block, check it with commands, merge accepted changes one at a time and deliver the main branch. You do not read or write code: your context must grow by single thousands of tokens per change, not by tens.

Runs on the session's main model; the dispatcher's work is mechanical, so start it with `/effort low`. The first message and the report name the session model; do not interrupt the work because of the model.

## Context discipline

- You read change artifacts only through the output of `sdd-dispatch-plan.py`: you do not open `proposal.md`, `specs/`, code, diffs, `tasks.md` or `verification.md`.
- No `cd`. In another folder use `git -C <path>` or a subshell `(cd <path> && …)`.
- Keep output short: `-q`, `--oneline`, `| tail -3`.
- You do not do the orchestrator's work: you do not fix code, tests, conflicts or artifacts.
- A hook blocked something: do not bypass it, neither with `SOLO_SDD_EXPENSIVE_OK` nor by rewording. Do what the hook requires, and write the block text into the report.

## Order

0. **Preparation.** Read `preparation.md` each time this step starts, also after compaction: the legacy tree stop, the delivery mode and merge method with their sources, the check commands, the run decisions file and the waiting file; a legacy tree means launch nobody.
1. **Subagent depth.** `echo "${CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH-unset}"`. Treat an empty or non-numeric value as set below 2. If it is unset or below 2, an orchestrator cannot launch the reviewer and search: launch nobody, create no worktree, and in the report under "Needs from you" write:
   - unset: once per computer run `solo-sdd install --hooks` and restart the session;
   - set below 2: name the current value and ask to raise it to 2 where the user set it (Claude Code settings or the environment): the script does not change a set value, do not suggest it.

   **Loopback.** Read the second line of the first plan (step 2), before the first wave; later recalculations ignore it. The fix for a blocked loopback: set `sandbox.network.allowLocalBinding: true` in the Claude Code settings, or run the session without the sandbox, then start a new session.
   - `loopback: ok`: go on.
   - `loopback: blocked (needed by the project): <error>`: the project's `AGENTS.md` has the item `- Loopback: needed` (section "Commands" or "Working copy"), its tests need local sockets: launch nobody, create no worktree, and in the report under "Needs from you" write the error and the fix.
   - `loopback: blocked: <error>`: the project declares no need: go on, and in the report under "Needs from you" write the line as a warning with the same fix.
2. **Pipeline.** `python3 ~/.local/bin/sdd-dispatch-plan.py <MAIN> --running <comma-separated ids: the orchestrator is working; in local mode also changes whose status was accepted before merge> [--waiting <comma-separated ids: only in pr mode, a change for which ship was started, until merge>] [--ignore-dep <id>:<name> ...] [--shared <path> ...]`: at the start, after every merge (successful or rolled back), after every orchestrator status and after every `ship` launch.

   Those in `--waiting` give conflicts like running ones, and take a slot only above the limit; the first output line is `limit: N, running: K, waiting for merge: W`, the second `loopback: …` (step 1), the third `delivery: …` (step 0); a broken `solo-sdd/config` gives exit 1 with `solo-sdd/config:<line>` and the reason: the user fixes it, launch nobody. A change is in only one list.

   Readiness, dependencies, conflicts, order and the limit are computed by the script; the limit is set by `dispatch.limit` of `solo-sdd/config`, else the "Orchestrators:" item (default 2), shared paths by "Shared:" of the `AGENTS.md` section "Working copy" (a path ending in `/` means all files under the directory). Lines `together: <id> and <id> — <path>` are pairs launched on a shared path: carry them into the report, a merge conflict may come there.

   A line `Artifacts outside git: <paths>` means these paths reach a worktree only as a copy by `sdd-worktree.py`: carry it into the report and continue. If there are `CLAIM abandoned: …` reasons and there has been no question about markers in this run yet, before the launch ask one question about all such markers by step 9. One question per run: markers abandoned after it stay in `waiting:`.

   The `--ignore-dep` and `--shared` keys of the user's answers (step 9) are passed in every recalculation until the end of the run.

   After a context summary, before the next recalculation, reread the last `## Run decisions` section of `<decisions file>` (step 0), from its heading to the end of the file: pass every key it holds and keep every decision without a key (a kept marker or dependency is not asked again). Earlier sections are not read: they are earlier runs' decisions.

   If there are `unknown dependency: …` reasons for changes not asked about yet, before the launch ask by step 9 in one window with the other questions of this plan (abandoned markers); a change answered "Keep" is not asked again.
3. **What to launch.** Exactly the changes from the `launch:` line, in its order.

   The `waiting:` line holds the waiting reasons (`CLAIM`, `CLAIM abandoned`, `WAITING`, `unknown dependency`, `depends on`, `conflict with`, `not merged: branch`, `not committed`, `limit`): they launch on the next recalculation; those not launched by the end of the work go into the report with the reason (a `not merged: branch` of a change already reported as `waits for human merge` is reported only that way; for `unknown dependency`, with the name), "not merged" with the branch and worktree, "not committed" with a request to commit the change folder: a worktree from a commit will not see it.

   `launch: none` and no running or waiting-for-merge changes: go to the report.
4. **Launch.** For every issued change, a branch and a worktree in a temporary folder, in two calls: `mktemp -d "${TMPDIR:-/tmp}/sdd-XXXXXX"` prints a folder `<D>` (an own folder per worktree, since a shared `${TMPDIR}/wt-<id>` is taken by leftovers of other projects), then `git worktree add -b change/<id> <D>/wt-<id>` with `MAIN` as the working folder and `<D>` written out literally: the `guard` hook lets through only this plain form (no `git -C`, `-q`, substitution or `cd` before a relative path).

   In `pr` mode before that `git -C <MAIN> fetch -q`, and `worktree add` is `git worktree add -b change/<id> <D>/wt-<id> origin/<main>`.

   An error: `git -C <MAIN> branch -D change/<id>` (git creates the branch even on failure, and it would block the change), the report says "not launched: worktree" with the error. `WORKTREE` is the absolute path from `git -C <MAIN> worktree list | grep "wt-<id>"`.

   Right after: `python3 ~/.local/bin/sdd-worktree.py setup <MAIN> <WORKTREE>`: it copies the git-ignored `solo-sdd/`, `AGENTS.md`, the paths of the "Working copy" section and individually ignored project documents (`.md`, `.txt`, `.rst`, `.adoc` up to 1 MiB, not `.env*`), links `node_modules` and `.venv`, runs the prepare command.

   Non-zero code: do not launch this change's orchestrator, run `python3 ~/.local/bin/sdd-worktree.py discard <MAIN> <WORKTREE>` (removes the worktree with the prepare files and the branch, on the next recalculation the change is in `launch:` again), the report says "not launched: worktree preparation" with the last error lines; if `discard` refused, the report adds its reason, the worktree and branch stay for the user; the other changes launch.

   Then the orchestrators of the issued changes, in one message, one `Agent` call per change:
   - `subagent_type: general-purpose`, `model: opus`, `run_in_background: true`, `description: Orchestrator <id>`;
   - do not set `isolation`: the dispatcher prepares the worktree itself with the `setup` command (`sdd-worktree.py`), a built-in one would lack the git-ignored artifacts;
   - `prompt` is the "Orchestrator prompt" below with the values filled in.
5. **Waiting.** An orchestrator's completion arrives as a notification. Do not poll their output files and do not read transcripts.
6. **Status acceptance.** The handback hook has already checked the commit, the archive and the removed `CLAIM` of `archived`. You repeat the checks:
   - `STATUS: archived`: save the status block to a file (`"${TMPDIR:-/tmp}/st-<id>.txt"`, through Write or a heredoc) and run `python3 ~/.local/bin/sdd-dispatch.py accept <file>`: the script itself runs the `VALIDATE` and `LIVE` commands in `WORKTREE` and checks the exit codes and output.

     A `LIVE` command that is not a code span of the `## Live Scenario` section of `<ARCHIVE>/verification.md` is a mismatch `not in the Live Scenario` and does not run; every command it runs stops after 600 s (`SDD_DISPATCH_TIMEOUT` sets other seconds) with the mismatch `<field>: timeout after <n> s`, and so does every `land-local` command (a check timeout is a red check).

     It does not run the `TESTS` command in any mode: the test suite is checked by the PR's CI in `pr` and by the checks after merge in `local`. Code 0 ("status matches"): the change goes to merge.
   - Code 1 (mismatches) or code 2 for an `archived` status (block not parsed): once `SendMessage` (if the tool is deferred, load it through `ToolSearch`) to this orchestrator (the address is its agent from the completion notification) with the command output: the mismatch lines (field, command, stated, got). The message continues the finished orchestrator with its context, the new status arrives as a notification; check it the same way. Code 1 or 2 again: the change is "not ready", the worktree and branch stay, the other changes go on.
   - `not_ready` and `blocked` are not rechecked: the reason from `NOTES` goes into the report, the worktree and branch stay. Continuing is possible only by the user's decision: ask at once by step 9.
   - A `Leftovers:` line under `NOTES` of a status of any kind (`archived`, `not_ready`, `blocked`) goes into "Needs from you" of the report with the change name; no such line, write nothing about leftovers.
   - Lines starting with `Lesson` under `NOTES` of a status of any kind go into the report line `Lessons:` with the change name.
7. **Merge one at a time**, in acceptance order: read `merge.md` each time this step starts, also after compaction: the `local` merge by `sdd-dispatch.py land-local` and its codes, the `pr` mode by `sdd-pr.py ship` and `land`, the return on conflict and the build failure after update; a change is merged only by these commands, and you do not fix "not merged" yourself.
8. **The pipeline runs** while there are running orchestrators, changes waiting for merge (`--waiting`) or changes in `launch:`; after every event, recalculate (step 2). In `local` mode a change whose status was accepted before merge is in `--running`: acceptance and merge go on this machine, it takes a slot. Merged changes in the archive unblock their dependants.
9. **Questions to the user.** Read `questions.md` each time this step starts, also after compaction: a decision needed from the user goes at once into an `AskUserQuestion` window with options, the recommended one first, and the answer into the run decisions file.
10. **Delivery** of the main branch by the `ship` skill, only in `local` mode (its `Promotion:` line, step 10 of `ship`, goes once into "Needs from you", the same as the `promotion:` line of `land` in `pr`); in `pr` everything is already on the remote, at the end `git -C <MAIN> rev-parse <main>` equals `origin/<main>`. No remote: delivery ends with the local branch, the report says "push not done: no remote". Push or merge triggers a prod deploy: stop before this action and ask the user, naming what rolls out and where.
11. **Report.** In status messages and in the report: "changes merged in this run: N in the local branch, M on the remote" (`local`: 0 on the remote until `ship`; `pr`: both numbers equal the number of merged PRs); do not write "all merged" if the remote has fewer.

## Orchestrator prompt

Read `orchestrator-prompt.md` each time step 4 launches an orchestrator, also after compaction: it holds the prompt and the status block an orchestrator hands back.

## Decisions without questions

| Thought | What to do |
|---|---|
| "The marker is abandoned, I will remove it myself" | No, one question to the user about all of them |
| "I will suggest it in text, the user will answer if needed" | No, a question window at once |
| "I will look at the diff to understand the status" | No. The status is checked by the commands from its fields |
| "The conflict is simple, I will fix it myself" | No. `land-local` already undid the merge (code 6), one return to the orchestrator with `refresh` |
| "The test is red, I will rerun it, maybe it is flaky" | No. `land-local` rolled back and checked on main: code 3 or 4 |
| "The user will agree anyway, I will merge myself" | No: code 8 waits for them |
| "I will do the merge in separate steps myself" | No. In `local`, one command `sdd-dispatch.py land-local` |
| "I will check the status myself: run the commands and `tail`" | No. `sdd-dispatch.py accept` |
| "I will launch everything ready at once" | Only what the script issued |
| "I will restart the orchestrator on the same change" | No. The branch `change/<id>` remains, the change waits for the user |
| "I will also launch the dependant, it is almost ready" | Only after the merge and archive of the dependency |
| "`isolation: worktree` is simpler" | Not for the dispatcher. The worktree is prepared by `setup` (`sdd-worktree.py`): a built-in one would lack the git-ignored artifacts |
| "I will rerun CI once more" | Once and only for `infra` |
| "The build after `refresh` failed, I will rebuild myself or rerun `ship`" | No. One return to the orchestrator with the command and the output lines; repeated, "not merged: PR" |
| "CodeQL is wrong, I will rerun CI or dismiss the alert" | No. One return to the orchestrator; dismissing the alert (`dismiss`) is the user's decision |
| "I will run the tests once more before merge" | No: CI or the check after merge checks them |
| "I will merge everything into the local main, PR later" | In `pr` mode, a PR right after acceptance |
| "I will glue the PR steps into one command" | No, only `ship` and `land` |
| "The context was summarised, I remember the keys" | No. Before the next recalculation reread the last `## Run decisions` section of the decisions file (step 0) and pass its keys |

## Report (in the user's language, in this form)

Read `report.md` each time you write the report (step 11), also after compaction: it holds the report form and what its columns show.
