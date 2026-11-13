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

0. **Preparation.** `MAIN` is `git rev-parse --show-toplevel`. Legacy tree: `MAIN` has `openspec/` and no `solo-sdd/`: stop before any change work, launch nobody, change no file and name the next step `solo-sdd import openspec`; do not import by yourself. From the project's `AGENTS.md` take the commands of the "Checks" section (and "Commands", if "Checks" refers to them): they are needed after every merge (`--check` of `land-local`). If none of them runs the tests, add the `Tests` row of "Commands" (never `Tests (one)`): tests are not repeated at acceptance.
   The delivery mode (`local` or `pr`) and the merge method (`squash`, `merge`, `rebase`) come first from the project settings: `(cd <MAIN> && solo-sdd config list)` prints `<key> <value> <source>`; `delivery.mode` and `delivery.merge` with the source `file`, `AGENTS.md` (the `Mode:` and `Merge:` items of its section "Delivery") or `mode` (a team project) apply (`solo-sdd config get delivery.mode` prints the value and, on stderr, `source: <source>`); the source `default` names nothing.

   The third line of the plan (step 2), `delivery: <mode> (<source>), merge: <method> (<source>)` with the sources `file`, `AGENTS.md`, `mode`, `default`, gives the same result. The section "Delivery" also gives the PR title rule and whether a merge into main triggers a deploy (and what rolls out; in `local` the merge goes into the local branch, only a push in `ship` can trigger a deploy).

   Nothing names the mode (the source `default`): `git -C <MAIN> remote` is empty means `local`; a remote exists means the mode is unknown: the first orchestrators start from the local main branch, right after them one question to the user (step 9) with the options `pr, squash`, `pr, merge`, `pr, rebase`, `local`; the mode applies from the first status acceptance.

   The remote's main branch is `git -C <MAIN> symbolic-ref --short refs/remotes/origin/HEAD` without `origin/`, otherwise the current one; below, `<main>`. A team line of branches: `delivery.base` with the source `file` (`solo-sdd config list`) is `<main>` instead: worktrees start from it, PRs and merges go into it (`sdd-worktree.py setup` and `sdd-pr.py` read it themselves, a broken file gives exit 1: the user fixes it).
   Record the answer to this question at once, so the next run does not ask it: a `## Delivery` section with the lines `- Mode: pr` and `- Merge: squash` (for `local`, only `- Mode: local`); do not invent other items. Where, by `git -C <MAIN> ls-files AGENTS.md` and `git -C <MAIN> status --short AGENTS.md`:
   - the first command is empty (the file is ignored by git or untracked): append the section to the end of `<MAIN>/AGENTS.md`, worktrees get it through `setup` and `refresh`;
   - the file is under git, the second is empty, mode `local`: append it and before the first merge commit only it into the local main branch: `git -C <MAIN> commit -qm "AGENTS.md: Delivery section" -- AGENTS.md`;
   - the file is under git, mode `pr` or the second command is not empty (someone else's uncommitted edits): do not touch the file or the main branch, the ready section text goes into "Needs from you" of the report.
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

   The `--ignore-dep` and `--shared` keys accumulated from the user's answers (step 9) are passed in every recalculation until the end of the run. If there are `unknown dependency: …` reasons for changes not asked about yet, before the launch ask by step 9 in one window with the other questions of this plan (abandoned markers); a change answered "Keep" is not asked again.
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
7. **Merge one at a time**, in acceptance order:
   - One command: `python3 ~/.local/bin/sdd-dispatch.py land-local <MAIN> <WORKTREE> <id> --check "<command>" ...`, one `--check` per command from step 0 (including the added test command).

     The script itself checks that `MAIN` is clean, merges with `--no-ff`, transfers (`sdd-worktree.py transport`), runs the checks and `solo-sdd validate --all` once each, rolls back on failure (`reset --keep` and `undo`) with a rerun of the failed check on main, and cleans up (`remove`, `branch -d`). In `local` mode the dispatcher does not run `git merge`, `reset --keep`, `transport`, `undo`, `remove` or `branch -d` itself.

     Carry the line `not transported: <files>` from the output, with any code, into the report and continue.
   - Code 0: `merged <hash>`, the worktree and branch removed; recalculate by step 2.
   - Code 2: "not merged: main folder not clean" with the files from the output: changed tracked files in `MAIN` are someone else's work.
   - Code 6: a merge or transfer conflict (the merge is already undone): "Return on conflict" with the files from the output.
   - Code 3: a check is red only with the change: one return to the orchestrator with the command, the failure lines from the output and the same branch update as in "Return on conflict"; a repeated code 3 means "not merged: checks" with the command.
   - Code 4: `main red: <command>`: do not launch or merge new changes, ask the user (step 9) with the command and the failure lines.
   - Code 8: "waits for the owner: <paths>": the branch touches a path from the "Owner only:" item of the "Delivery" section of the main folder's `AGENTS.md`, `.github/workflows/**` or changes the item itself, or `AGENTS.md` has the old pre-English item (the line names `solo-sdd migrate-agents`: the user does the migration).

     The merge has not started, the branch and worktree are in place (the line `not merged: waits for human merge: branch change/<id>` under `delivery.merge-by: human`: the same, the report shows `waits for human merge` and "Needs from you" says merge the branch `change/<id>` by hand). Do not repeat or bypass; the change goes into the report table and into "Needs from you": review and merge the branch `change/<id>`. The other changes go on; those depending on it wait for its archive in the main branch, as with any unmerged change.
   - Code 1: the script's line into the report: "not merged: <step>" or "merged, not cleaned: <step>".
   - Do not rerun checks "until green": a "flaky test" is recognised only with code 4.
   - You do not fix "not merged" yourself: the worktree and branch stay for the user, the other changes continue.

   **`pr` mode** (instead of the local merge above; `local` reads unchanged). If by "Delivery" a merge into main triggers a deploy, ask the user before the first merge (step 9): what rolls out and where.
   - Right after an accepted status, as a background Bash command with `run_in_background: true`: `python3 ~/.local/bin/sdd-pr.py ship <MAIN> <WORKTREE> <main> "<title by the rule>"`; the other changes go on, the result arrives as a notification.

     From the `ship` launch the change moves from `--running` to `--waiting` and stays there until merge or code 8 `waits for human merge` from `land`, including on repeated `ship` and `wait` without an orchestrator; recalculate by step 2 at once: the freed slot goes to the next change. A return to the orchestrator (conflict, `red`, `codeql`, a build failure after update) puts it back into `--running` until a new `ship`; "not merged" means in no list.

     From the summary line `PR #<n> <url> CI: <result>` take `<url>` for `land`. Code 6: "Return on conflict" with the files from the output. Code 1: "not merged: PR" with the step and the reason from the output, not "CI: infra"; the exception is code 1 at the `refresh` step with the line `after refresh: <command> — code <n>` or `— timeout`: that is the "Build failure after update" below.
   - `green`: one at a time, in acceptance order: `python3 ~/.local/bin/sdd-pr.py land <MAIN> <WORKTREE> <url> <method>`. Carry the line "code scanning alerts not checked" after `green` into the report: `land` goes as usual.

     Code 0: merged, the worktree and branch removed; carry the line `not transported: <files>` into the report; the line `promotion: <base> → <next>: sdd-pr.py promote <base> <next>` (printed when `delivery.promote` is set) goes once into "Needs from you": do not run `promote` and do not merge promotion PRs, that is the user's step; recalculate by step 2.

     Code 5 (main moved ahead): `ship` in the background again and `land` after a new `green`. Code 1: "not merged: merge" with the reason.

     Code 8 from `land`: "waits for the owner: <paths>" (including because of the old pre-English item, the line names `solo-sdd migrate-agents`): the PR stays open, "Needs from you" says review and merge the PR with the link (do not confuse it with code 8 `codeql` from `ship` and `wait`: those are other commands).

     Code 8 with `waits for human merge: <url>` (`delivery.merge-by: human`, the team default: a person merges): the change is not failed, the report shows `waits for human merge` with the URL, the PR stays open and green, the worktree and branch stay; do not merge, repeat or bypass it.

     "Needs from you": merge the PR, then `python3 ~/.local/bin/sdd-pr.py land <MAIN> <WORKTREE> <url> --after-merge` (it pulls, transports and removes the worktree; an open PR gives code 8 again); the change leaves `--waiting` and is in no list, like "not merged" (changes depending on it wait for its archive in the main branch), recalculate by step 2 and go on with the next change; a run where only such changes are left goes to the report.

     Code 7: the change counts as merged (it is on the remote), `land` is repeated once; a repeated code 7 means cleanup with the step and the reason in "Needs from you" of the report; recalculate by step 2.
   - `red` (code 3): one return to the orchestrator with the failure lines from the `ship` output; after a new status, `sdd-pr.py ship` in the background again. A repeated `red` means "not merged: CI" with the PR link.

     `infra` (code 4): one rerun without edits: `gh run rerun --failed <run>` (run is the number after `/actions/runs/` in `gh pr checks <url> --json link`), then `python3 ~/.local/bin/sdd-pr.py wait <url>` in the background; a repeated one means "not merged: CI (infrastructure)".

     If the `infra` output has "required check did not start: <name>", there is no failed run: instead of this rerun, one empty commit `git -C <WORKTREE> commit --allow-empty -m "ci: rerun checks"` and `ship` in the background again; repeated, "not merged: CI (infrastructure)". The results of `wait` read the same as the results of `ship`: codes 0, 3, 4, 8.
   - `codeql` (code 8): the checks passed, but code scanning alerts are open on the PR: one return to the orchestrator with the lines `#<number> <rule> <file>:<line> <text>` from the `ship` or `wait` output, `land` is not called; after a new status, `sdd-pr.py ship` in the background again. A repeated `codeql` means "not merged: CodeQL" with the PR link, without a second return and without a CI rerun: an alert is a finding in the code, not a runner failure.
   - Checks after merge are CI and the acceptance in WORKTREE after the update; they are not repeated locally: a merged PR cannot be rolled back.

   **Return on conflict** (merge or transfer): once `SendMessage` to the orchestrator: "update the branch from main: `git -C <WORKTREE> merge <main branch>` (in `pr` mode, `git -C <WORKTREE> fetch -q` and `origin/<main>`), then `python3 ~/.local/bin/sdd-worktree.py refresh <MAIN> <WORKTREE>`
   (code 3: the named files: with markers, merge them; deleted on one side, bring them to the main folder or leave the conflict to the user;
   code 4: the "After refresh:" command failed, the transfer is already done: the last lines of the `refresh` output name the command, its code or timeout and its output; if this change already had a return for "Build failure after update", at once `STATUS: not_ready` with the same, otherwise fix the build in WORKTREE by them and repeat `refresh`;
   code 4 again, hand back `STATUS: not_ready`, with the command and the code or timeout in `NOTES` and the output lines as a separate line `Output: …` under `NOTES` above the line limit), resolve the conflict in WORKTREE, repeat the checks and hand back the status again".

   In `pr` mode the conflict comes from `ship` with code 6, the new status after the return goes to `ship` again. The new status is checked as usual (step 6). A repeated conflict in the same files as last time, or the third for the change: "not merged: conflict" with the files, the worktree and branch stay. A conflict in other files, because main moved ahead after the return: one more return.

   A `refresh` code 4 inside this return counts as the return for "Build failure after update" below: `not_ready` with code 4 in `NOTES` or a `refresh` step failure in the next `ship` is a repeated failure, "not merged: PR" with the command and the output lines (from `NOTES` and `Output:` or from the `ship` output) in the report, no second return.

   **Build failure after update** (`sdd-worktree.py refresh` code 4; in `pr` mode, `ship` with code 1 at the `refresh` step and the line `after refresh: <command> — code <n>` or `— timeout`): once `SendMessage` to the orchestrator: "after the branch update the "After refresh:" command failed: `<command>` — <code or timeout>;
   output: <the command's output lines from the `refresh` or `ship` output>. The branch is already updated, the artifacts are transferred; fix the build in WORKTREE on the updated branch, check `python3 ~/.local/bin/sdd-worktree.py refresh <MAIN> <WORKTREE>` (code 0), repeat the checks and hand back the status again".

   The new status is checked as usual (step 6), then `ship` in the background again. A repeated failure means "not merged: PR" with the command and the output lines in the report, no second return.

   The return for a build failure is one per change on all paths: if a `refresh` code 4 already happened in the return for a conflict, this failure is a repeated one.
8. **The pipeline runs** while there are running orchestrators, changes waiting for merge (`--waiting`) or changes in `launch:`; after every event, recalculate (step 2). In `local` mode a change whose status was accepted before merge is in `--running`: acceptance and merge go on this machine, it takes a slot. Merged changes in the archive unblock their dependants.
9. **Questions to the user.** A decision needed from the user goes at once into an `AskUserQuestion` window (deferred: load it through `ToolSearch`) with options, the recommended one first. The orchestrators work in the background; their statuses, merges and launches come after the answer. No window (a `claude -p` session): the question goes as the first line of the message marked "Needs from you", the other changes continue without waiting.
   Abandoned markers: the options `Remove and launch` (recommended) and `Keep`, the question text holds the ids and reasons from `waiting:`.
   - "Remove and launch": recalculate by step 2, `rm <MAIN>/solo-sdd/changes/<id>/CLAIM` only for those named in the question whose reason is still `CLAIM abandoned` (do not touch live markers), recalculate again.
   - "Keep": the markers stay, the change stays in `waiting:` until the end of the run and in the report with the reason, the question is not repeated.
   - No window: the question as a "Needs from you" line, the markers are not removed: that is "Keep".

   Unknown dependencies (`unknown dependency` in `waiting:`): names marked "a spec, not a change" get one question, options `Ignore` (recommended) and `Keep`; other names get one question, `Keep` (recommended) and `Ignore`: it could be a typo in a real dependency. One kind of names, one question; both kinds, two questions in one window. The question text holds the ids and names from `waiting:`.
   - "Ignore": `--ignore-dep <id>:<name>` until the end of the run, recalculate, the line "Remove from Depends On: <names>" in this change's orchestrator prompt; `MAIN` files are not edited.
   - "Keep": the change stays in `waiting:` until the end of the run and in the report, the question is not repeated.
   - No window: a "Needs from you" line, that is "Keep".

   A proposal to change the course of the run that you cannot accept yourself (running in parallel changes the plan holds because of a shared file, taking new changes into the run, stopping the run) goes into a window at the moment you formulated it, not as a line in a status message. For a shared file the options are `Treat <path> as shared until the end of the run` (`--shared <path>`, recalculate) and `One at a time`. Nothing is launched against the script's plan.

   You do not need to edit `proposal.md` or `AGENTS.md`: the user writes the file into "Shared:", suggest it in "Needs from you" of the report.
10. **Delivery** of the main branch by the `ship` skill, only in `local` mode (its `Promotion:` line, step 10 of `ship`, goes once into "Needs from you", the same as the `promotion:` line of `land` in `pr`); in `pr` everything is already on the remote, at the end `git -C <MAIN> rev-parse <main>` equals `origin/<main>`. No remote: delivery ends with the local branch, the report says "push not done: no remote". Push or merge triggers a prod deploy: stop before this action and ask the user, naming what rolls out and where.
11. **Report.** In status messages and in the report: "changes merged in this run: N in the local branch, M on the remote" (`local`: 0 on the remote until `ship`; `pr`: both numbers equal the number of merged PRs); do not write "all merged" if the remote has fewer.

## Orchestrator prompt

```
You are the Opus orchestrator of change <ID>. Mode: "Under the dispatcher" of the spec-next skill.

MAIN: <absolute path of the main folder>
WORKTREE: <absolute path of the worktree>
BRANCH: change/<ID>

[A line only for a change answered "Ignore" on an unknown dependency, otherwise absent: Remove from Depends On: <names>]
Run the spec-next skill for change <ID> by its "Under the dispatcher" section. All code, artifacts and commits go in WORKTREE; CLAIM goes in MAIN/solo-sdd/changes/<ID>/CLAIM.

WORKTREE is prepared: solo-sdd/, AGENTS.md and the node_modules links are already in place. Do not prepare the environment; if something is missing, STATUS: blocked with what is missing. In MAIN write only CLAIM; edit AGENTS.md, documents and specs in WORKTREE. Do not delete or commit the node_modules and .venv links. Do not merge into the main branch, do not run /ship, do not start the next change.

A hook blocked a subagent launch or a command: do not bypass it (neither SOLO_SDD_EXPENSIVE_OK nor rewording). Do what the hook requires and record the block in HOOKS.

Do not print the spec-next report. As the last message return only this block:

STATUS: archived | not_ready | blocked
CHANGE: <id>
BRANCH: <branch>
WORKTREE: <absolute path>
COMMIT: <hash of the branch's last commit>
ARCHIVE: <the change folder in solo-sdd/changes/archive, relative to WORKTREE>
VALIDATE: solo-sdd validate --all -> exit <code>
TESTS: <the `Tests` row of AGENTS.md> -> exit <code> [a note after a space, for example (250 tests)]
LIVE: <one command from the WORKTREE root without &&, ||, ;, | and cd; for a complex scenario, a stand call> -> <what it printed>
REVIEW: done <n> of <m> | <findings in one line>
AGENTS: <whom you launched: role, model, count>
HOOKS: <what the hooks blocked and what you did> | none
NOT_VERIFIED: nothing | <what>
NOTES: <up to 3 lines; for not_ready and blocked, what is in the way>
Leftovers: <above the NOTES limit: what is left, process, port, folder; no leftovers, no line>
Lesson…: <above the NOTES limit: the Lesson lines of the spec-next report, one each; no lesson, no line>
```

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

## Report (in the user's language, in this form)

```
Dispatcher: <model>
| Change | Launch | STATUS | Status check | Merge (`pr`: PR link and result) | Agents | Hooks | Acceptance |
Not launched: <id — reason> | none
Launched together on a shared path: <`together:` lines> | none
Artifacts outside git: <paths> | none
Not transported: <id — the `not transported:` line from `transport`> | none
Returned to orchestrators: <id — reason: status, conflict, checks, CI, CodeQL> | none
Hook blocks: <text and what was done> | none
Lessons: <id — the `Lesson` line from the status> | none
Open PRs of the run: <links> | none
Delivery mode: local|pr (source: `solo-sdd/config` | the "Delivery" section | `mode: team` | no remote | the user's answer); N in the local branch, M on the remote
Delivery: <by ship> | push not done: no remote | waits for deploy consent: <what and where>
git log --oneline --graph -20: <output>
git worktree list: <output>
git status --short: <output or "empty">
Needs from you: <action; the `promotion:` line (`land` in `pr`, `ship` in `local`), once; step 0 left the mode answer unrecorded: the ready text of the "Delivery" section; "Leftovers:" lines with the change name; a change with code 8: the PR with the link or the branch `change/<id>`> | nothing
```

"Launch" is the launch sequence number. The CI result in the Merge column is `green`, `red`, `infra` or `codeql`; a change with code 8 shows "waits for the owner: <paths>" or `waits for human merge` with the PR URL (in `local`, the branch). An unmerged change in the table comes with its worktree path and branch: the user sorts them out.
