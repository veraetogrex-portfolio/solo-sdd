---
name: ship
description: Use when the user asks to commit, push, open or merge a pull request, or sync the local branch with the remote - "commit", "push", "make a commit and push", "make a pr", "merge the request", "sync with git", "why are you not pushing", "and who will merge" - or when finished work is still sitting uncommitted in the working tree.
---

# ship: from the working tree to a merged main

Done when the local main branch matches the remote and the working tree has no unexplained file. An open PR without a merge is "not done". The exceptions: push or merge rolls out to prod, and there is no deploy consent; the project's `delivery.merge-by` is `human`, and the PR is green (step 7).

## Order

1. **Repository rules.** Read `AGENTS.md`, `CLAUDE.md`, `CONTRIBUTING`, the branch rules. They decide whether to push directly or through a PR, and the message format.

   A project with `solo-sdd/` sets the delivery in its settings: `solo-sdd config list` prints `<key> <value> <source>`; `delivery.mode` (`pr`: through a PR, `local`: push the main branch directly) and `delivery.merge` (the merge method: `squash`, `merge`, `rebase`) with the source `file`, `AGENTS.md` (the `Mode:` and `Merge:` items of its `## Delivery` section) or `mode` (a team project) apply (`solo-sdd config get delivery.mode` prints the value and, on stderr, `source: <source>`).

   The source `default` names nothing: the other repository rules above decide.
2. **Deploy.** Find what runs on push or merge of any affected branch: `.github/workflows`, `.gitlab-ci.yml`, git hooks, hosting autodeploy, the project rules. If it is a prod rollout, stop before this push or merge and ask: what rolls out, to which server, what happens to the data. First prepare the checked changes and the commit for review; consent is required before the action that triggers the deploy. Until consent the PR stays open, if creating it does not trigger a deploy.
3. **Inventory.** `git status` and `git diff --stat`. Every changed file gets one of two: it goes into the commit or is named in the report with the reason it was left.

   Integrations: in a project with `solo-sdd/` where `solo-sdd config get integrations` is not empty, then `solo-sdd check --point ship`. Code 1 (a `gate` FAIL) stops before the commit: not done, and the report names the integration of each `FAIL <name>:` line. A tree already recorded for the point is reused without a new run (`reused <tree>`).
4. **Secrets.** `.env`, keys, certificates, local agent settings excluded from git do not go into a commit. Found a secret in the diff: stop and say so.
5. **Commits.** Group by meaning, the message in the style of the repository history.
6. **Push.** No `--force`. Rejected: `git pull --rebase`, resolve conflicts, repeat.
7. **PR.** If needed. A project with `solo-sdd/` (`delivery.mode` `pr`, or the repository rules choose a PR) goes only through the PR tool, so its gates apply: human merge, main moved ahead, code scanning, `Owner only:` paths, checklists; the `gh` PR commands are never called directly there, and the `guard` hook refuses a direct merge.

   `python3 ~/.local/bin/sdd-pr.py open <working folder of the branch> <main branch> "<title>"` pushes the branch and prints `PR #<n> <url>`; `python3 ~/.local/bin/sdd-pr.py wait <url>`: 0 green, 3 red (fix, push, repeat `wait`), 4 infra (rerun the failed run, repeat `wait`), 8 code scanning alerts (fix them, push, repeat `wait`); `python3 ~/.local/bin/sdd-pr.py merge <url> <the merge method of step 1> <git rev-parse HEAD>`.

   Merge codes: 0 merged; 5 main moved ahead: `git fetch origin`, `git merge origin/<main branch>`, push, then `wait` and `merge` again; 8 (`waits for human merge`, `waits for the owner: …`, `checklist <name>: …`): stop with the printed line, the PR stays open for the owner, the report says `PR: <link>, waits for human merge` for a human merge and `PR: <link>, <printed line>` otherwise, skip steps 8 and 9 until a person merges, then `git pull` the main branch; 1: stop, not done, with the printed reason.

   A repository without `solo-sdd/` merges as before: `gh pr create`, wait for the checks, merge yourself with `gh pr merge`. Do not turn on auto-merge.
8. **Sync.** Switch to the main branch, `git pull`.
9. **Check.** `git fetch && git status` is clean, `git rev-parse HEAD` equals `git rev-parse origin/<main>`.
10. **Promotion.** A project with `solo-sdd/` and `delivery.promote` in `solo-sdd config list`: the main branch above is `delivery.base` (empty: the remote's default branch). After the merge into it the report has the line `promotion: <base> → <next>: sdd-pr.py promote <base> <next>` with the first branch of `delivery.promote` (`release/*` is passed as is: `promote` takes the newest `release/` branch). Do not run it and do not merge the promotion PR: that is the user's step.

## If it did not work

| Situation | Action |
|---|---|
| Merge or push is blocked by the agent's permissions | Name the exact permission line to add, and repeat after |
| PR checks failed | Fix and push into the same branch |
| The tree has others' changes | Do not roll back. Commit yours, list the others in the report |
| No remote repository | Check the config and the project history. Address not found: record a blocker, do not create an external repository without a request |
| Push or merge triggers a prod deploy | Stop before this action, ask. Give the prepared changes and the PR link, if it is open, in the report |

## Report

```
Commits: <hash — message>
PR: <link, merged> | not needed | open, waits for deploy consent | <link>, waits for human merge | <link>, <the code 8 line of sdd-pr.py merge>
Deploy: not triggered | triggered with consent, checked by <scenario> | waits for consent
Local and server: match | diverge — <why>
Not committed: <file — reason> | nothing
Integrations ship: PASS | advice FAIL <name> | stopped before the commit: FAIL <name> | none enabled
Promotion: promotion: <base> → <next>: sdd-pr.py promote <base> <next> | not set
```
