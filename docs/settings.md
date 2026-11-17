# Settings

A project keeps its settings in `solo-sdd/config`: one `key: value` per line, lines starting with `#` are comments, a list value is separated by commas. No file means all defaults. The value in effect is the file value, else the key's item of the `AGENTS.md` section "Delivery" (`Mode:`, `Merge:`, `PR title:`, `Deploy:`, `Owner only:`), else the team default under `mode: team`, else the default.

`solo-sdd config list` prints every key as `<key> <value> <source>` with the source `file`, `AGENTS.md`, `mode` or `default`; `get <key>` prints the value, and `source: <source>` on stderr; `set <key> <value>` and `unset <key>` change only that line and keep comments, order and line endings. `describe [<key>]` explains every key, or the one named: its group, what it changes, its type with the allowed values, the default, the team default and the value in effect with its source; then each checklist pattern and each checklist key set in the file. `list --json` prints the rows of `list` with the same fields as a list of objects. A wrong key or value is refused with exit code 1 and the allowed keys or values, the file unchanged.

`solo-sdd settings` shows the same keys on a full-screen terminal screen and changes them the same way, one edited line per key: a key whose file value overrides a Delivery item of `AGENTS.md` is marked with that item, picking `delivery.mode: pr` without a CI workflow shows the warning `init` prints, a file changed on disk since the screen read it is not overwritten, and a broken file opens read-only with its line and reason. Its Machine section (`m`) shows the agents laid out, the hooks and the global rules with the layout's source, version and copy counts and the `warn` and `fail` lines of `doctor`, and applies a change by running `solo-sdd uninstall --hooks`, `uninstall --global-rules` and `install --agents …` after it lists them with the folders they change. Its update check switch is saved at once and turns the version check of the home menu and `doctor` off or on ([Update check](cli.md#update-check)); the version line there comes from the cache, without a request.

A model key (`agents.*-model`) takes one model name of ASCII letters, digits, `.`, `-`, `_`, `[` and `]`; a project narrows the models of a role within the machine lists of `~/.claude/hooks/model-policy.json`, never widens them: the `guard` hook refuses a launch on a set orchestrator, review or lookup model outside its list, naming the key and the list, unless the owner set `SOLO_SDD_EXPENSIVE_OK=1`.

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
| `delivery.branch-prefix` | a branch prefix git takes a name after | `change/` | | `sdd-dispatch-plan.py` (a branch `<prefix><id>` holds the change), `sdd-dispatch.py land-local`, `sdd-pr.py land` (deletes only such a local branch), `sdd-eval.py`, `spec-dispatch`; `config set`, `config unset` and `solo-sdd settings` refuse a new value while an open change has a branch under the old one, or when it equals `delivery.plan-prefix` |
| `delivery.plan-prefix` | a branch prefix git takes a name after | `plan/` | | `spec-plan`: the branch of the plan commit under `delivery.mode: pr` is `<prefix><first id>` |
| `dispatch.limit` | a whole number from 1 | `2` | | `sdd-dispatch-plan.py` (the `limit:` line); the `Orchestrators:` item of the `AGENTS.md` section "Working copy" |
| `process.review-rounds` | a whole number from 1 | `5` | | `spec-next`: the most independent acceptance rounds, plus one extra round after the second or later when every open `Important` lies only in the lines of the last rework |
| `process.light-path` | `on`, `off` | `on` | | the global rules and `spec-plan`: `off` sends every code edit through a change |
| `process.light-path.max-files` | a whole number from 1 | `3` | | the global rules and `spec-plan`: the most files a light path edit changes |
| `process.max-tasks` | a whole number from 3 | `10` | | `solo-sdd validate` (`too many tasks: <n> > <limit> (<source>)`), `spec-plan`, `spec-analyze` and the algorithm: the most tasks of one change |
| `process.bugfix-max-tasks` | a whole number from 3 | `5` | | `spec-plan` and `spec-analyze`: the most tasks of a bug fix change; the smaller of it and `process.max-tasks` holds |
| `process.requirement-max-chars` | a whole number from 100 | `500` | | `solo-sdd validate` (`requirement too long: <name>: <n> > <limit> (<source>)`), `spec-plan` and `spec-analyze`: the most characters of one requirement text |
| `process.audit-every` | a whole number from 1 | `5` | | `spec-next`: `Time for: /spec-audit on the main specs` when the archive count after its archive is a multiple of it |
| `process.analyze` | `on`, `off` | `on` | | `spec-plan` and `spec-next`: `off` skips the `spec-analyze` pass and the report holds `Analyze: off (solo-sdd/config)`; the `Depends On` check stays. An agent changes `process.max-tasks`, `process.bugfix-max-tasks`, `process.requirement-max-chars`, `process.audit-every` and `process.analyze` only on the owner's words |
| `commit.light-prefix` | one line, at most 200 characters | `light:` | | the global rules, the algorithm, `spec-plan`, `work-status` and `report`: a light path commit subject starts with it, matched as plain text, not a pattern |
| `reply.language` | `ru`, `en`, `off` | `off` | | the `stop` hook: the language of the final reply, `off` checks none; the `SOLO_SDD_REPLY_LANG` variable |
| `agents` | `claude`, `codex`, `cursor`, `other` | the detected agents | | `doctor` (`warn project-agents` for an agent the installation lacks) |
| `rules.scope` | `project`, `global` | `project` | | `init`: `project` writes the rules block into `AGENTS.md`, `global` writes none and names the global rules (`install --global-rules`) |
| `agents.orchestrator-model` | one model name of ASCII letters, digits, . - _ [ and ] | `opus` | | `spec-dispatch`: the `model` of each orchestrator launch; the `guard` hook refuses a launch on a set model outside the `main` list of the machine's `model-policy.json` |
| `agents.review-model` | one model name | the session's main model | | `spec-next` step 7a and `spec-audit`: the `model` of the `Review:` subagent, none when empty; the `guard` hook: the `main` list |
| `agents.lookup-model` | one model name | `haiku` | | `spec-next` and the global rules: the `model` of a `Lookup:` subagent; the `guard` hook: the `cheap` list |
| `agents.test-model` | one model name | `haiku` | | the global rules: paid product calls in tests, acceptance and experiments; the Test model allowlist of the `guard` hook bounds it |
| `agents.dispatcher-effort` | `low`, `medium`, `high` | `low` | | `spec-dispatch`: the `/effort` the dispatcher session starts with |
| `agents.executor` | `self`, `codex` | `self` | | `spec-next`, `spec-plan`, `codex-orchestration`, the algorithm and the global rules: `codex` counts as the owner naming `codex-orchestration`; an agent changes the key only on the owner's words in the chat |
| `integrations` | integration names, separated by commas | none | | `solo-sdd integrations`: the enabled integrations, see [Integrations](integrations.md) |
| `integrations.off` | integration names, separated by commas | none | | `solo-sdd integrations`: the bundled integrations switched off, see [Integrations](integrations.md) |
| `git.ignore` | .gitignore patterns, separated by commas; an item starting with ! keeps a path in git | `.claude/worktrees/, .env, .env.*, !.env.example` | | `solo-sdd ignore`, `init` and `project-init`: the lines of the solo-sdd block of `.gitignore`, see [Commands](cli.md); an item that hides `AGENTS.md`, `CLAUDE.md` or a path of `solo-sdd/` other than `solo-sdd/changes/archive/` by git's matching (checked against the process layout: a capability or change folder name counts for a pattern of two or more names), or starts with #, is refused; `config set`, `unset` and the settings screen print `run: solo-sdd ignore --write` |

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
