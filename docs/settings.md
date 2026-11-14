# Settings

A project keeps its settings in `solo-sdd/config`: one `key: value` per line, lines starting with `#` are comments, a list value is separated by commas. No file means all defaults. The value in effect is the file value, else for `delivery.mode` and `delivery.merge` the `Mode:` or `Merge:` item of the `AGENTS.md` section "Delivery", else the team default under `mode: team`, else the default.

`solo-sdd config list` prints every key as `<key> <value> <source>` with the source `file`, `AGENTS.md`, `mode` or `default`; `get <key>` prints the value, and `source: <source>` on stderr; `set <key> <value>` and `unset <key>` change only that line and keep comments, order and line endings. `describe [<key>]` explains every key, or the one named: its group, what it changes, its type with the allowed values, the default, the team default and the value in effect with its source; then each checklist pattern and each checklist key set in the file. `list --json` prints the rows of `list` with the same fields as a list of objects. A wrong key or value is refused with exit code 1 and the allowed keys or values, the file unchanged.

A line that is not `key: value`, an unknown key or a wrong value makes the command and the scripts fail with `solo-sdd/config:<line>` and the reason; the hooks take the defaults and write the reason to `~/.claude/hook-state/errors.log`. The file is read with the standard library only: the hooks run on `/usr/bin/python3` 3.9.

| Key | Values | Default | Team default | Read by, and the older source used when the key is not in the file |
|---|---|---|---|---|
| `mode` | `solo`, `team` | `solo` | | the team defaults of the other keys |
| `delivery.mode` | `local`, `pr` | `local` | `pr` | `sdd-dispatch-plan.py` (the `delivery:` line, each value with its source `file`, `AGENTS.md`, `mode` or `default`), `spec-dispatch`, `ship`; the `Mode:` item of the `AGENTS.md` section "Delivery" |
| `delivery.merge` | `squash`, `merge`, `rebase` | `squash` | | the same; the `Merge:` item of the section "Delivery" |
| `delivery.merge-by` | `agent`, `human` | `agent` | `human` | `sdd-pr.py merge` and `land` (`human`: code 8 `waits for human merge`, `land --after-merge` finishes after a person merged), `sdd-dispatch.py land-local`, `spec-dispatch`, `ship`, the `stop` hook (no return for an open PR) |
| `delivery.base` | a branch name | the remote's default branch | | `sdd-worktree.py setup` (the worktree start), `sdd-pr.py open`, `ship`, `land` (the PR target and the update), `spec-dispatch`, `ship` |
| `delivery.promote` | branch names in order; release/* means the newest release/ branch by version | none | | the `promotion:` line of `sdd-pr.py land`, `spec-dispatch` and `ship` after a merge into the base: the next branch and its `sdd-pr.py promote` command |
| `dispatch.limit` | a whole number from 1 | `2` | | `sdd-dispatch-plan.py` (the `limit:` line); the `Orchestrators:` item of the `AGENTS.md` section "Working copy" |
| `process.review-rounds` | a whole number from 1 | `3` | | `spec-next`: the most independent acceptance rounds |
| `process.light-path` | `on`, `off` | `on` | | the global rules and `spec-plan`: `off` sends every code edit through a change |
| `process.light-path.max-files` | a whole number from 1 | `3` | | the global rules and `spec-plan`: the most files a light path edit changes |
| `reply.language` | `ru`, `en`, `off` | `off` | | the `stop` hook: the language of the final reply, `off` checks none; the `SOLO_SDD_REPLY_LANG` variable |
| `agents` | `claude`, `codex`, `cursor`, `other` | the detected agents | | `doctor` (`warn project-agents` for an agent the installation lacks) |
| `rules.scope` | `project`, `global` | `project` | | `init`: `project` writes the rules block into `AGENTS.md`, `global` writes none and names the global rules (`install --global-rules`) |
| `integrations` | integration names, separated by commas | none | | `solo-sdd integrations`: the enabled integrations, see [Integrations](integrations.md) |
| `integrations.off` | integration names, separated by commas | none | | `solo-sdd integrations`: the bundled integrations switched off, see [Integrations](integrations.md) |

## Checklists

A checklist names files a person checks by a list before they merge. Two keys per checklist, `<name>` in lowercase letters, digits and `-`:

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
