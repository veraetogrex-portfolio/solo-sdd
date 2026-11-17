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
Run decisions: <file> — <lines of the run's section> | none
Open PRs of the run: <links> | none
Delivery mode: local|pr (source: `solo-sdd/config` | the "Delivery" section | `mode: team` | no remote | the user's answer); N in the local branch, M on the remote
Delivery: <by ship> | push not done: no remote | waits for deploy consent: <what and where>
git log --oneline --graph -20: <output>
git worktree list: <output>
git status --short: <output or "empty">
Needs from you: <action; the `promotion:` line (`land` in `pr`, `ship` in `local`), once; step 0 left the mode answer unrecorded: the ready text of the "Delivery" section; "Leftovers:" lines with the change name; a change with code 8: the PR with the link or the branch `change/<id>` (`delivery.branch-prefix`)> | nothing
```

"Launch" is the launch sequence number. The CI result in the Merge column is `green`, `none`, `red`, `infra` or `codeql`; a change with code 8 shows "waits for the owner: <paths>" or `waits for human merge` with the PR URL (in `local`, the branch). An unmerged change in the table comes with its worktree path and branch: the user sorts them out.
