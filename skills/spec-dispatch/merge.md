7. **Merge one at a time**, in acceptance order:
   - One command: `python3 ~/.local/bin/sdd-dispatch.py land-local <MAIN> <WORKTREE> <id> --check "<command>" ...`, one `--check` per command from step 0 (including the added test command).

     The script itself checks that `MAIN` is clean, merges by `delivery.local-merge` (`merge` with `--no-ff` by default, `squash`, `rebase`), transfers (`sdd-worktree.py transport`), runs the checks and `solo-sdd validate --all` once each, rolls back on failure (`reset --keep` and `undo`) with a rerun of the failed check on main, and cleans up (`remove`, `branch -d`; `-D` after a squash or rebase). In `local` mode the dispatcher does not run `git merge`, `reset --keep`, `transport`, `undo`, `remove` or `branch -d` itself.

     Carry the line `not transported: <files>` from the output, with any code, into the report and continue.
   - Code 0: `merged <hash>`, the worktree and branch removed; recalculate by step 2.
   - Code 2: "not merged: main folder not clean" with the files from the output: changed tracked files in `MAIN` are someone else's work.
   - Code 6: a merge or transfer conflict (the merge is already undone): "Return on conflict" with the files from the output.
   - Code 3: a check is red only with the change: one return to the orchestrator with the command, the failure lines from the output and the same branch update as in "Return on conflict"; a repeated code 3 means "not merged: checks" with the command.
   - Code 4: `main red: <command>`: do not launch or merge new changes, ask the user (step 9) with the command and the failure lines.
   - Code 8: "waits for the owner: <paths>": the branch touches a path of `solo-sdd config get delivery.owner-only` in `MAIN` (the old source: the "Owner only:" item of the "Delivery" section of the main folder's `AGENTS.md`), `.github/workflows/**` or `solo-sdd/config`, or changes the item itself, or `AGENTS.md` has the old pre-English item (the line names `solo-sdd migrate-agents`: the user does the migration).

     The merge has not started, the branch and worktree are in place (the line `not merged: waits for human merge: branch change/<id>` under `delivery.merge-by: human`: the same, the report shows `waits for human merge` and "Needs from you" says merge the branch `change/<id>` by hand). Do not repeat or bypass; the change goes into the report table and into "Needs from you": review and merge the branch `change/<id>`. The other changes go on; those depending on it wait for its archive in the main branch, as with any unmerged change.
   - Code 1: the script's line into the report: "not merged: <step>" or "merged, not cleaned: <step>".
   - Do not rerun checks "until green": a "flaky test" is recognised only with code 4.
   - You do not fix "not merged" yourself: the worktree and branch stay for the user, the other changes continue.

   **`pr` mode** (instead of the local merge above; `local` reads unchanged). If `delivery.deploy` (`solo-sdd config get delivery.deploy` in `MAIN`, step 1) says a merge into main triggers a deploy, ask the user before the first merge (step 9): what rolls out and where.
   - Right after an accepted status, as a background Bash command with `run_in_background: true`: `python3 ~/.local/bin/sdd-pr.py ship <MAIN> <WORKTREE> <main> "<title by the rule>"`; the other changes go on, the result arrives as a notification.

     From the `ship` launch the change moves from `--running` to `--waiting` and stays there until merge or code 8 `waits for human merge` from `land`, including on repeated `ship` and `wait` without an orchestrator; recalculate by step 2 at once: the freed slot goes to the next change. A return to the orchestrator (conflict, `red`, `codeql`, a build failure after update) puts it back into `--running` until a new `ship`; "not merged" means in no list.

     From the summary line `PR #<n> <url> CI: <result>` take `<url>` for `land`. Code 6: "Return on conflict" with the files from the output. Code 1: "not merged: PR" with the step and the reason from the output, not "CI: infra"; the exception is code 1 at the `refresh` step with the line `after refresh: <command> — code <n>` or `— timeout`: that is the "Build failure after update" below.
   - `green` or `none`: one at a time, in acceptance order (`none`: no checks under `delivery.require-ci: off`; alert lines after `green` under `delivery.code-scanning: warn` go into the report): `python3 ~/.local/bin/sdd-pr.py land <MAIN> <WORKTREE> <url> <method>`. Carry the line "code scanning alerts not checked" after `green` into the report: `land` goes as usual.

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
