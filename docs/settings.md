# Settings

A project keeps its settings in `solo-sdd/config`: one `key: value` per line, lines starting with `#` are comments, a list value is separated by commas. No file means all defaults. The value in effect is the file value, else the key's item of the `AGENTS.md` section "Delivery" (`Mode:`, `Merge:`, `PR title:`, `Deploy:`, `Owner only:`), else the team default under `mode: team`, else the default.

`solo-sdd config list` prints every key as `<key> <value> <source>` with the source `file`, `AGENTS.md`, `mode` or `default`; `get <key>` prints the value, and `source: <source>` on stderr; `set <key> <value>` and `unset <key>` change only that line and keep comments, order and line endings. `describe [<key>]` explains every key, or the one named: its group, what it changes, its type with the allowed values, the default, the team default and the value in effect with its source; then each checklist pattern and each checklist key set in the file. `list --json` prints the rows of `list` with the same fields as a list of objects. A wrong key or value is refused with exit code 1 and the allowed keys or values, the file unchanged.

`solo-sdd settings` shows the same keys on a full-screen terminal screen and changes them the same way, one edited line per key: a key whose file value overrides a Delivery item of `AGENTS.md` is marked with that item, picking `delivery.mode: pr` without a CI workflow shows the warning `init` prints, a file changed on disk since the screen read it is not overwritten, and a broken file opens read-only with its line and reason. Its Machine section (`m`) shows the agents laid out, the hooks and the global rules with the layout's source, version and copy counts and the `warn` and `fail` lines of `doctor`, and applies a change by running `solo-sdd uninstall --hooks`, `uninstall --global-rules` and `install --agents …` after it lists them with the folders they change. Its update check switch is saved at once and turns the version check of the home menu and `doctor` off or on ([Update check](cli.md#update-check)); the version line there comes from the cache, without a request.

A text key (`delivery.pr-title`, `delivery.deploy`) takes one line of printable characters, at most 200, with the ends trimmed; its `AGENTS.md` item is read trimmed and as written, without the limit.

A line that is not `key: value`, an unknown key or a wrong value makes the command and the scripts fail with `solo-sdd/config:<line>` and the reason; the hooks take the defaults and write the reason to `~/.claude/hook-state/errors.log`. The file is read with the standard library only: the hooks run on `/usr/bin/python3` 3.9.

| Key | Values | Default | Team default | Read by, and the older source used when the key is not in the file |
|---|---|---|---|---|
| `mode` | `solo`, `team` | `solo` | | the team defaults of the other keys |
| `delivery.mode` | `local`, `pr` | `local` | `pr` | `sdd-dispatch-plan.py` (the `delivery:` line, each value with its source `file`, `AGENTS.md`, `mode` or `default`), `spec-dispatch`, `ship`; the `Mode:` item of the `AGENTS.md` section "Delivery" |
| `delivery.merge` | `squash`, `merge`, `rebase` | `squash` | | the same, for a pull request; the `Merge:` item of the section "Delivery" |
| `delivery.local-merge` | `merge`, `squash`, `rebase` | `merge` | | `sdd-dispatch.py land-local`: `merge` makes a merge commit (`git merge --no-ff`), `squash` one commit titled by the last own commit of the branch, `rebase` rebases the branch in a temporary worktree, moves the change worktree to it with `reset --keep` and fast-forwards; a conflict in any of them rolls back with code 6; after `squash` and `rebase` the branch is deleted with `-D` |
| `delivery.merge-by` | `agent`, `human` | `agent` | `human` | `sdd-pr.py merge` and `land` (`human`: code 8 `waits for human merge`, `land --after-merge` finishes after a person merged), `sdd-dispatch.py land-local`, `spec-dispatch`, `ship`, the `stop` hook (no return for an open PR) |
| `delivery.base` | a branch name | the remote's default branch | | `sdd-worktree.py setup` (the worktree start), `sdd-pr.py open`, `ship`, `land` (the PR target and the update), `spec-dispatch`, `ship` |
| `delivery.promote` | branch names in order; release/* means the newest release/ branch by version | none | | the `promotion:` line of `sdd-pr.py land`, `spec-dispatch` and `ship` after a merge into the base: the next branch and its `sdd-pr.py promote` command |
| `delivery.pr-title` | one line, at most 200 characters | `the change name` | | `ship` and `spec-dispatch`: the rule of the pull request title; the `PR title:` item of the section "Delivery" |
| `delivery.deploy` | one line, at most 200 characters | `no` | | `ship`, `spec-dispatch` and `project-init`: what a push or a merge deploys and where, so the agent stops before it and asks; the `Deploy:` item of the section "Delivery" |
| `delivery.owner-only` | relative paths, separated by commas, * within a name, ** across folders | none | | `sdd-pr.py merge` and `land`, `sdd-dispatch.py land-local`: a merge of a change touching these paths, `.github/workflows/**` or `solo-sdd/config` itself waits for the owner (code 8); always read from the main folder, never from the PR or the worktree; the backquoted paths of every `Owner only:` item of the section "Delivery" |
| `delivery.ci-timeout` | a whole number of seconds from 1 | `1200` | | `sdd-pr.py wait` and `ship`: the most seconds CI gets before `CI: infra`; a `--timeout` flag of `wait` wins; a stderr line `limits: …` names each limit with its source `flag`, `file` or `default` while one of the three keys is set; read from the main folder |
| `delivery.ci-stuck` | a whole number of seconds from 1 | `300` | | `sdd-pr.py wait` and `ship`: how long a required check may stay missing or not started after the others finished; a `--stuck` flag wins; no limit extends `delivery.ci-timeout` |
| `delivery.ci-no-checks` | a whole number of seconds from 1 | `180` | | `sdd-pr.py wait` and `ship`: how long a PR may show no checks at all before `CI: infra` "no checks", or `CI: none` under `delivery.require-ci: off` |
| `delivery.require-ci` | `on`, `off` | `on` | | `sdd-pr.py wait`, `ship`, `merge` and `land`: `off` gives `CI: none` with code 0 and merges a PR without any check while the base branch requires none and its rules were read; a red, pending or missing required check still blocks; `spec-dispatch` lands on `none` as on `green` |
| `delivery.code-scanning` | `gate`, `warn`, `off` | `gate` | | `sdd-pr.py wait` and `ship` after green checks: `gate` gives `CI: codeql` and code 8 on an open alert, `warn` prints `CI: green` with the alert lines and code 0, `off` does not ask for alerts |
| `delivery.delete-branch` | `on`, `off` | `on` | | `sdd-pr.py merge` and `land`: `off` keeps the remote and the local branch after the merge; `sdd-dispatch.py land-local` always deletes |
| `delivery.draft` | `on`, `off` | `off` | | `sdd-pr.py open` and `ship` create the PR as a draft (`gh pr create --draft`); `merge` and `land` mark it ready (`gh pr ready`) after every gate, right before the merge request; a failed ready request: code 1, no merge |
| `dispatch.limit` | a whole number from 1 | `2` | | `sdd-dispatch-plan.py` (the `limit:` line); the `Orchestrators:` item of the `AGENTS.md` section "Working copy" |
| `process.review-rounds` | a whole number from 1 | `5` | | `spec-next`: the most independent acceptance rounds, plus one extra round after the second or later when every open `Important` lies only in the lines of the last rework |
| `process.light-path` | `on`, `off` | `on` | | the global rules and `spec-plan`: `off` sends every code edit through a change |
| `process.light-path.max-files` | a whole number from 1 | `3` | | the global rules and `spec-plan`: the most files a light path edit changes |
| `reply.language` | `ru`, `en`, `off` | `off` | | the `stop` hook: the language of the final reply, `off` checks none; the `SOLO_SDD_REPLY_LANG` variable |
| `agents` | `claude`, `codex`, `cursor`, `other` | the detected agents | | `doctor` (`warn project-agents` for an agent the installation lacks) |
| `rules.scope` | `project`, `global` | `project` | | `init`: `project` writes the rules block into `AGENTS.md`, `global` writes none and names the global rules (`install --global-rules`) |
| `integrations` | integration names, separated by commas | none | | `solo-sdd integrations`: the enabled integrations, see [Integrations](integrations.md) |
| `integrations.off` | integration names, separated by commas | none | | `solo-sdd integrations`: the bundled integrations switched off, see [Integrations](integrations.md) |

## Checklists

A checklist names files a person checks by a list before they merge. Two keys per checklist, `<name>` in lowercase letters, digits and `-`; the Checklists section of `solo-sdd settings` (`c`) adds one by its name, paths and file, edits and removes one, and marks a checklist without one of its keys as incomplete and a file that does not exist as missing:

| Key | Value |
|---|---|
| `checklist.<name>.paths` | globs of repository paths, separated by commas (`*` within a name, `**` across folders) |
| `checklist.<name>.file` | a markdown file of `- [ ]` items, from the repository root |

```
checklist.money-safety.paths: billing/**, src/payments/*.py
checklist.money-safety.file: docs/checklists/money-safety.md
```

```
- [ ] Amounts are in minor units, never floats
- [ ] A repeated charge request is idempotent
- [ ] The charge and its refund are logged
```

When a PR's files match the paths (or change the checklist file itself or `solo-sdd/config`), `sdd-pr.py open` and `ship` append to the PR body a section `## Checklist: <name>` with the file's items, unticked; a section already in the body is never rewritten.

`sdd-pr.py merge` and `land` exit with code 8 and `checklist <name>: <n> open items` while an item of the file is not ticked with its own text in the section: a removed, emptied or rewritten section counts its missing items as open, and an extra unticked line is open too. A checklist with one of its two keys, or a file unreadable or without items, stops `open`, `ship` and `merge` with code 1. The settings and the file are read from the main folder, not from the PR.

When every item is ticked, `merge` and `land` still exit with code 8 and `checklist <name>: no approval on <sha>` until the PR has an approving review on its head commit by an account other than the PR author: only the latest review of each account counts (a comment-only review after an approval also needs a fresh approval, stricter than GitHub), a new commit needs a new approval, and reviews that cannot be read count as none.

GitHub does not let the author approve their own PR, so the approval is a person's even when the agent pushes from the author's account; the ticks guide the reviewer, the approval is the gate. A solo project therefore needs a second person (or a second account) to approve a PR that touches a checklist's paths.

`/ship` in a project with `solo-sdd/` merges through `sdd-pr.py open`, `wait` and `merge`, so these gates apply on the ordinary path too, and the `guard` hook refuses `gh pr merge` and a `gh api` call to `pulls/<n>/merge` there. A merge the guard does not read (the GraphQL `mergePullRequest` mutation, a wrapper script, the GitHub web page) still bypasses every `sdd-pr.py` gate; branch protection with required reviews closes that.
