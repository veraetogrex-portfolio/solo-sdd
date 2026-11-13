# solo-sdd

solo-sdd is a spec-driven development process for one person or a team working with AI coding agents: Claude Code, Codex and any agent that reads `AGENTS.md`. It ships the rules, skills, hooks and a process format with its own validator, and it counts a change as done only after a live check and a review by an agent that did not write the code.

## Quick start

You need Python 3.9+, git and a coding agent.

```bash
pip install solo-sdd
solo-sdd install
cd ~/code/my-project
solo-sdd init
```

`solo-sdd install` puts the skills into the agent folders of your home. `solo-sdd init` sets up the process in the project's git repository: it proposes the settings and asks three questions, Enter accepts each proposal. Then, inside the project, in the agent:

1. `/project-init`: the project rules in `AGENTS.md` and `.env.example`.
2. `/spec-plan` with a plan, a bug list or an idea: a queue of small changes in `solo-sdd/changes/`.
3. `/spec-next`: one change from selection to archive: code, tests, a live check, a review by another agent, delivery.

To see one full change cycle before your own code, run the demo: [examples/demo/WALKTHROUGH.md](https://github.com/veraetogrex-portfolio/solo-sdd/blob/main/examples/demo/WALKTHROUGH.md), about five minutes.

Other ways to install: [Installation](#installation). The init questions and flags: [First project](#first-project).

## What solo-sdd does

- **Done means proven.** A change is closed only when its live scenario passed on real input or a stand and an agent that did not write the code accepted it requirement by requirement. Green tests alone are "not done" ([ALGORITHM.md](https://github.com/veraetogrex-portfolio/solo-sdd/blob/main/ALGORITHM.md), Principles 4, 7 and 10).
- **The spec is the source of truth.** Main specs live in `solo-sdd/specs/`, a change carries its delta specs, a verification plan written before the code and at most 10 tasks; `solo-sdd archive` applies the deltas to the main specs.
- **Own format and validator.** `solo-sdd validate` checks the process tree (the main specs and the open changes) with the Python standard library, no other program; `solo-sdd new`, `list` and `archive` cover the cycle.
- **No questions in the middle of work.** The agent decides, records each decision in the change and asks only before paid calls, deleting data or an action on prod.
- **Hooks enforce the rules.** In Claude Code, after `solo-sdd install --hooks`, the hooks refuse edits to a change another session claimed, the wrong model for a review and a premature "done" status, and return the agent while work is left; [process protection](#claude-code-process-protection) blocks direct process kills.
- **Several agents, one process.** Claude Code, Codex and other agents read the same rules and skills; `solo` and `team` modes set how changes are delivered: local merges, pull requests, a merge by a person.
- **A dispatcher for parallel work.** `/spec-dispatch` runs ready changes in parallel, up to the `dispatch.limit` setting, one orchestrator per change in its own worktree, accepts each status by rerunning its checks and delivers each change through a pull request with CI or a local merge.

## Requirements

- Python 3.9+, git; Node 20+ only for the solo-sdd npm wrapper.
- Claude Code, Codex or another agent that reads `AGENTS.md`, see [Supported agents](#supported-agents).

Some skills use extra tools (all optional, needed only for their own skill):

- `gh` (GitHub CLI): `pr` mode of `spec-dispatch` and `sdd_pr.py`, PRs in `ship`;
- `codex` (Codex CLI) — `codex-orchestration`;
- a browser for automation: `ui-check`;
- a style skill for a language other than English: that language in `copy-check`;
- `docker compose`: `health` and `debug-profile`, if the project runs through it;

## Installation

Where the files go: [docs/layout.md](https://github.com/veraetogrex-portfolio/solo-sdd/blob/main/docs/layout.md).

The package is on PyPI and npm under the name `solo-sdd` and installs with one command:

```bash
pip install solo-sdd
uv tool install solo-sdd
pipx install solo-sdd
```

Through npm:

```bash
npm i -g solo-sdd
```

The unreleased `main` installs from the git address: `pip install git+https://github.com/veraetogrex-portfolio/solo-sdd` or `npm i -g github:veraetogrex-portfolio/solo-sdd`.

The npm package is a wrapper over the same `python3 -m solo_sdd`: it needs Python 3.9+ in `PATH` (or its path in `SOLO_SDD_PYTHON`) and Node 20+. Without a suitable Python the command prints `solo-sdd: Python 3.9+ needed (found: …)` and exits with code 1.

The same works from a clone without installation: `python3 -m solo_sdd <command>`. The clone stays the way to develop, `sync.py` works as before.

## Supported agents

<!-- generated from solo_sdd/providers.py; tests/test_providers.py compares -->
| Agent | Detected by | Skills | Global rules | Project rules | Hooks | Subagents |
|---|---|---|---|---|---|---|
| `claude` | `claude` in PATH or `~/.claude` | `~/.claude/skills` | `~/.claude/CLAUDE.md` | `CLAUDE.md` | 2.1.312 | 2.1.312 |
| `codex` | `codex` in PATH or `~/.codex` | `~/.codex/skills` | `~/.codex/AGENTS.md` | `AGENTS.md` | unverified | 0.159.2 |
| `cursor` | `cursor-agent` in PATH or `~/.cursor` | unverified | unverified | unverified | unverified | unverified |
| `other` | always | `~/.agents/skills` | `~/AGENTS.md` | `AGENTS.md` | unverified | unverified |

`install --agents claude,codex` deploys for the named agents plus `other`; without `--agents` it keeps the choice of the last install, and a first install takes the detected agents plus `other`. A deployment from a version without the choice counts as `claude`, `codex`, `other`. The choice is kept in `~/.local/share/solo-sdd/state.json`; `status`, `update`, `sync.py push` and `doctor` follow it, `uninstall` removes the copies of every agent.

Dropping an agent from the choice removes its unchanged copies; an edited copy is kept and named. An unknown name exits with code 1 and the known names, no file changes; so does a choice without `claude` with `--hooks` or while the hooks are connected (`uninstall` removes them). A skill that needs capabilities gets deployed only where they are present: `spec-dispatch` needs subagents and hooks (`needs` in `targets.json`).

`doctor` prints `ok agent <name>` when hooks and subagents are both present, else `warn agent <name>: no <capability>: <what is not enforced>`. The versions are those `tests/stands/provider-probe.py` ran: subagents from `claude --help` and `codex features list`, hooks from a no-op hook in a temporary home; `unverified` means the probe did not see it work.

`cursor` has not been probed: no Cursor was available, so `install --agents cursor` deploys only the `other` files, says that project rules come from `solo-sdd init`, `doctor` prints `warn agent cursor: unverified: skills, project rules: …` before the `no hooks` and `no subagents` gaps, and `tests/stands/provider-probe.py cursor` prints `not run` for each capability, installing nothing.

A file laid out into skill folders (the bundled copies under `integrations/`) is added to `targets.json["files"]` as one line naming each skill and the path inside its folder, never an agent folder: `"integrations/antislop/antislop.md": {"skills": {"ui-check": "antislop/core.md", "copy-check": "antislop/core.md"}}`. It goes to every agent that skill's `SKILL.md` goes to and to no other, so a new agent needs no edit there. A line naming a skill absent from `skills` stops `install`, `status` and `sync.py push` with code 1 and the line named, nothing written.

## First project

The quick start step by step, after `solo-sdd install`.

1. In the project's git repository run `solo-sdd init`. It looks at the project first: the agents installed, the git remote, protection of the default branch (through `gh`, `unknown` without it), the distinct commit author emails of the last 90 days, a `CODEOWNERS` file (root, `.github/` or `docs/`) and a CI workflow (a `*.yml` or `*.yaml` file directly in `.github/workflows/`).

   From that it proposes `mode: team` for 2 or more authors, `CODEOWNERS` or a protected default branch, else `solo`; the agents found; `delivery.mode: pr` with a remote and a CI workflow, else `local`. A remote without a workflow, or `pr` chosen without one, prints that `pr` needs a CI workflow: `sdd-pr.py merge` refuses a PR without checks. On a terminal it asks three questions with the proposal in brackets, Enter accepts it:

   ```
   mode: proposed solo (1 author in 90 days, no CODEOWNERS, default branch not protected)
   mode (solo, team) [solo]:
   agents: proposed claude, codex, other (claude: claude in PATH, codex: ~/.codex, other: always)
   agents (claude, codex, cursor, other) [claude, codex, other]:
   delivery.mode: proposed pr (remote origin, CI .github/workflows/test.yml)
   delivery.mode (local, pr) [pr]:
   ```

   `solo-sdd/config` gets each value under a comment naming the fact behind it. Without a terminal, or with `--yes`, the proposals are taken without questions. Flags override them: `--solo` or `--team`, `--agents claude,codex`, `--delivery local|pr`, and `--set key=value` (repeatable) for any key of "Settings"; a wrong value is refused with exit code 1 before any file is written. For scripts and CI:

   ```
   solo-sdd init --yes --team --agents claude --set dispatch.limit=3
   ```

   A repeat keeps an existing `solo-sdd/config` byte for byte, flags included; `solo-sdd init --reconfigure` asks the three questions and then every other key, each with the value in effect in brackets, and changes only the lines whose answer differs.
2. In Claude Code or Codex run `/project-init`: project rules, `AGENTS.md`, `.env.example`.
3. `/spec-plan`: a plan into a queue of small changes.
4. `/spec-next`: a change from selection to archive.

## Rules

The solo-sdd rules (`global/AGENTS.md`) go into the projects that chose solo-sdd, not into the home folder. `solo-sdd init` writes them as a block between markers at the end of the project's `AGENTS.md` and creates `CLAUDE.md` with the line `@AGENTS.md` when the project has none, so Claude Code reads the same file; an existing `CLAUDE.md` is not changed. Text outside the block keeps every byte.

`solo-sdd/rules-block` records the block written last: a repeated `init` after a package upgrade updates an unchanged older block, while an edited block, broken or erased markers are named as `drift` and left as they are. `install` and `update` do not touch projects: run `solo-sdd init` in a project to refresh its block. In `team` mode the block is committed with the repository.

The setting `rules.scope: global` (see "Settings") makes `init` write no block and name the global rules as the source.

Global rules are opt-in. `solo-sdd install --global-rules` writes the same block into `~/.claude/CLAUDE.md`, `~/.codex/AGENTS.md` and `~/AGENTS.md` (only for the chosen agents); text outside the block does not change, a missing file is created. The choice is kept in the state (`_global_rules`), so a later `install`, `update` or `sync.py push` keeps the block up to date; a home that has the block from an earlier version keeps getting it without the flag.

`solo-sdd uninstall --global-rules` removes only the block and returns the files byte for byte (an edited block is kept and named); a later `install` writes no global rules. For example, on a new machine:

```
solo-sdd install
cd ~/code/my-project
solo-sdd init --yes
```

`--hooks` adds to `~/.claude/settings.json` the workflow hooks, the subagent depth (`env.CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH`), an `autoMode.allow` rule and `statusLine` (see [docs/layout.md](https://github.com/veraetogrex-portfolio/solo-sdd/blob/main/docs/layout.md)). `uninstall` removes exactly this and returns the file byte for byte; copies edited in place are kept and named. `--purge` also removes the `solo` schema and `~/.local/share/solo-sdd`.

The hooks can be connected without the deployment too: `python3 global/work_hooks_settings.py` does the same with `settings.json`. If the file does not exist, it is created.

## Settings

A project keeps its settings in `solo-sdd/config`: one `key: value` per line, lines starting with `#` are comments, a list value is separated by commas. No file means all defaults. The value in effect is the file value, else for `delivery.mode` and `delivery.merge` the `Mode:` or `Merge:` item of the `AGENTS.md` section "Delivery", else the team default under `mode: team`, else the default.

`solo-sdd config list` prints every key as `<key> <value> <source>` with the source `file`, `AGENTS.md`, `mode` or `default`; `get <key>` prints the value, and `source: <source>` on stderr; `set <key> <value>` and `unset <key>` change only that line and keep comments, order and line endings. A wrong key or value is refused with exit code 1 and the allowed keys or values, the file unchanged.

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
| `integrations` | integration names, separated by commas | none | | `solo-sdd integrations`: the enabled integrations, see [Integrations](#integrations) |
| `integrations.off` | integration names, separated by commas | none | | `solo-sdd integrations`: the bundled integrations switched off, see [Integrations](#integrations) |

### Checklists

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

## Integrations

An integration plugs an outside tool or rule set into solo-sdd without naming it in solo-sdd: a folder `<name>/` with a file `integration` and its own material, in the project's `solo-sdd/integrations/` or in the owner's `~/.local/share/solo-sdd/integrations/`. When both hold the same name, the project one is used and the owner one is shadowed. A found integration stays disabled until the `integrations` setting of `solo-sdd/config` names it, an owner one included.

Bundled: the package ships two pinned copies as integrations in its own `integrations/` folder, a third source below the other two: `antislop` (`points: review`, `tags: ui, copy`, the anti-slop rules `ui-check`, `copy-check` and the reviewer read) and `security-audit` (`points: audit`, `tags: security`, the method of the `spec-audit` security pass).
A bundled one is enabled unless the `integrations.off` setting names it; `integrations disable <name>` adds it there, `enable <name>` removes it, and a project or owner folder with the same name shadows it. When one is off in a project, the skills that read it say in their report that its rules are off there.

The file has one `key: value` per line, lines starting with `#` are comments:

| Key | Value | Default |
|---|---|---|
| `name` | the folder name: lowercase letters, digits and `-`, not starting with `-` | required |
| `about` | one line saying what it does, shown by `integrations list` | required |
| `points` | where it is called, separated by commas: `checks`, `review`, `ship`, `audit` | required |
| `command` | a shell command; required for `checks` and `ship` | none |
| `material` | a path inside the folder; required for `review` and `audit` | none |
| `applies` | globs of the changed files it is called for, separated by commas | any file |
| `requires` | the program it needs on `PATH` | none |
| `mode` | `gate` (a failure holds the step) or `advice` | `advice` |
| `missing` | when `requires` is not found: `warn` or `fail` | `warn` |
| `timeout` | seconds, a whole number from 1 | `120` |
| `output` | lines of its output kept, a whole number from 1 | `20` |
| `tags` | names that `check --tag` selects by, separated by commas | none |

A fictional `marker-check` in `solo-sdd/integrations/marker-check/integration`:

```
name: marker-check
about: refuses a line with the marker DO-NOT-SHIP
points: checks, ship
command: sh "$SOLO_SDD_INTEGRATION_DIR/check.sh"
applies: *.py
```

A line that is not `key: value`, an unknown or repeated key, a wrong value, a missing required key, a control character, a file over 64 KiB, not UTF-8, a link or not a regular file, a project folder linked out of the project, or a `material` leaving the folder is refused with the file, the line and the key, never skipped.

`solo-sdd integrations list` prints one line `<name> <source> enabled|disabled <points>: <about>` per found integration, a shadowed copy as `<name> <source> shadowed by the <source> copy`, and exits 1 with the reason for a broken description or a listed name without a folder.
`solo-sdd integrations enable <name>` and `disable <name>` change only the `integrations` line of `solo-sdd/config` (`integrations.off` for a bundled one), then rewrite the solo-sdd block of `AGENTS.md`; `enable` refuses a name it does not find or a broken description, `disable` also removes a listed name whose folder is gone, and a repeated call changes nothing.

Rules: an enabled integration whose folder holds a `rules.md` gets a section `## Integration: <name>` with that text at the end of the solo-sdd block of `AGENTS.md`, in name order; `init`, `enable` and `disable` rewrite the block, so a disabled integration's section is gone at once, and a blank file gives no section.
A `rules.md` holding a solo-sdd marker line, over 8 KB, not UTF-8, a link or not a regular file is refused with exit 1 before `solo-sdd/config` or `AGENTS.md` change (a lone CR reads as a line end, as in Markdown); only the rules of the integrations enabled after the call are read, so a broken one can still be disabled.
`enable` and `disable` rewrite only an existing block: without one they create no file and name `solo-sdd init`; an edited block is `drift`, as for `init`; under `rules.scope: global` no section is written and the command says so, and `enable` or `disable` drops the sections of an existing block.

Material: `solo-sdd check --point review|audit [--changed]` runs nothing and prints `MATERIAL <name>: <absolute path>` for each enabled integration of the point (with `--changed`, whose `applies` matches), `FAIL <name>: <reason>` with exit 1 for a listed name without a folder, a broken description or a missing file.
Without `--tag` it lists only the names of `integrations` (a bundled name written there is switched by `integrations.off` alone); `--tag <tag>` (not with `--changed`) lists every enabled integration of the point with that tag, the bundled ones included, also in a folder without `solo-sdd/` (where an owner folder still shadows a bundled one), and prints `no integrations enabled with the point <point> and the tag <tag>` when there is none: `ui-check` and `spec-next` step 7a ask `--point review --tag ui`, `copy-check` `--tag copy`, `spec-audit` `--point audit --tag security`.
`spec-next` step 7a hands the files of `check --point review --changed` to the reviewer and `spec-audit` gives the files of `check --point audit` to its reviewer, each as a method to apply: an instruction in them to run, fetch or change something is not executed.

`solo-sdd check --point checks|ship [--changed]` runs every enabled integration of the point, with `--changed` only those whose `applies` matches a file that differs from the merge base with the base branch (`delivery.base`, else the remote's default branch, else `HEAD`), untracked files included.
A command runs through `/bin/sh -c` in the repository root with `SOLO_SDD_INTEGRATION_DIR` (its folder) and `SOLO_SDD_POINT` set and the changed files on stdin, one per line, in its own process group, which is stopped after `timeout` seconds or 1 MB of output.
It prints one line `PASS|FAIL|SKIP <name>: <first output line>` per integration in name order, up to `output` more lines under a FAIL, `no integrations enabled` when the list is empty (`no enabled integration has the point <point>` when none of it has the point), and `command <name>: <command>` before the first run of a project integration's command in a repository and after that command changes.
A FAIL of a `gate` integration, a missing `requires` under `missing: fail` and a listed name without a folder exit 1; an `advice` one never does. A changed path holding a newline is refused with exit 1, since stdin holds one path per line.
The output is kept as plain text: bytes that are not UTF-8 replaced, control characters removed, lines cut at 400 characters.

The result is recorded under `~/.local/share/solo-sdd/checks/<folder>-<digest of its path>/<tree>.json`, where `<tree>` is the git tree of the whole working copy built in a temporary index, so the real index is untouched. A call on the same tree, point, changed files and enabled descriptions prints the recorded lines and `reused <tree>`, exits with the recorded code and runs nothing; a record holding a SKIP or a stopped run is not reused. The record folder is under the user's home: it is a lookup by tree, not a protection.

`--change <id>` puts one line `Integrations <point> (tree <hash>): <name> PASS|FAIL|SKIP, …` into the `## Result` section of `solo-sdd/changes/<id>/verification.md`, replacing that point's previous line and keeping every other line;
since the line changes the working tree, the point is recorded under the new tree too.
A name that is not an open change, a `verification.md` without `## Result`, or a Result section where the line would stand inside a comment or a code block is refused with exit 1 before any run. A call that runs nothing (no integration enabled, none with the point, none applies) writes no line.

The process calls it at two points, and only when the `integrations` setting is not empty: `spec-next` step 6 runs `solo-sdd check --point checks --changed --change <id>` after the suite, a `gate` FAIL holds the step like a red test, and step 7a hands the printed lines, `advice` ones included, to the reviewer, who runs no integration;
`ship` runs `solo-sdd check --point ship` after the inventory, and a `gate` FAIL stops before the commit.
The `stop` hook returns the agent once when an enabled `checks` integration's `applies` matches a file the session edited that `check --changed` sees (one differing from the base) and no record of the point `checks` exists for the current tree, naming `solo-sdd check --point checks --changed`;
a broken description or config is written to `errors.log` and gives no reason.

Inside a project `solo-sdd doctor` prints `ok integrations: none enabled` when nothing is enabled, and one row per enabled integration, the bundled ones on by default included: `ok integration <name>: <source>, points <points>, requires <program> found, last run PASS|FAIL <date>|none`, then `, command <command>` for a project one.
The row is `warn` with `requires <program> missing` when the program is not on `PATH`, and says `requires none` when there is no `requires`. The last run is the newest PASS or FAIL of the integration in the repository's records folder, dated by the run of its point (a record from before the point's `time` by the file's write); a SKIP is not a run.
A broken project integration (enabled or not), a broken enabled owner one, an owner folder that cannot be listed while an enabled name is not in the project, and an enabled name without a folder give a `fail integration <name>: <reason>` row each (`<name>` is `-` for a source folder that cannot be listed, the reason of a broken description starts with `<file>:<line>:`), the other rows stay, and `doctor` exits 1; a broken owner integration the project does not enable shows only in `integrations list`.
The same errors reach the SessionStart context of a project with a `solo-sdd/` tree as one line `integration errors: <first error>`, with `; <n> in all` when there are more; a failed read of them is written to `errors.log` and the rest of the context stays.

Skills: each `skills/<skill>/SKILL.md` of an owner integration (`~/.local/share/solo-sdd/integrations/<name>/`) is laid out by `solo-sdd install` and `update` into the skill root of every chosen agent, enabled in a project or not, with the drift, backup and foreign-file rules of the solo-sdd skills; `solo-sdd status` shows each copy on a row named `integration:<name>`. A project integration's skills are not laid out, since the agents' skill folders serve every project.
A skill is refused and named, the other copies still laid out, when its name is taken by a solo-sdd skill or by an integration earlier in name order, its folder name breaks the `name` rule, its `skills` folder, skill folder or `SKILL.md` is a link, or its `SKILL.md` is missing, not a regular file, over 1 MB or not UTF-8; a broken description lays out none of its skills and is named when it has a `skills` folder.
When the integration folder or a skill is gone or refused, the next `update` removes each unedited copy it laid out and names the path; an edited one is kept as `drift`, and a source it lacks the permission to read (a folder it cannot list or enter, a closed file) keeps its copies, keeps their names from integrations later in name order and is named.

## Moving from OpenSpec

A project that keeps its process in `openspec/` moves with one command, history included:

1. `solo-sdd import openspec`: prints the plan (the counts of specs, open and archived changes, every file it would create) and writes nothing.
2. `solo-sdd import openspec . --write`: creates `solo-sdd/`. `specs/` and `changes/` with the archive are copied byte for byte without the `.openspec.yaml` files; `project.md` gets the `context` of `openspec/config.yaml` with the `Language:` and `Mode:` lines first; `openspec/analyze.md` becomes `solo-sdd/analyze.md`; a change whose `.openspec.yaml` has `skip_specs: true` gets `Specs: none` under `## Capabilities`; `CLAIM` and `WAITING` stay.
3. `solo-sdd validate --all`, then delete `openspec/` yourself: the import never touches it.

A repeat prints `nothing to import`. A non-empty `solo-sdd/` that differs from the plan (a changed, extra or missing file) is refused with exit code 1 and the first differing path, nothing written; so is a linked folder inside `openspec/` or a file that is not UTF-8 text where the import reads it. The `operations` of `config.yaml` and the `openspec` words inside the texts are not converted.

## Commands

| Command | What it does |
|---|---|
| `solo-sdd install [--agents a,b] [--hooks] [--global-rules] [--replace-foreign]` | Deploys skills, scripts and templates for the chosen agents (the global rules only with `--global-rules`, see below), see [Supported agents](#supported-agents), without any external program |
| `solo-sdd init [folder] [flags]` | In the project's git repository creates the missing ones of `solo-sdd/project.md`, `solo-sdd/analyze.md`, `solo-sdd/specs/`, `solo-sdd/changes/` and `docs/waiting.md` from the templates and `solo-sdd/config` with the proposed settings (see "First project"), one `created` line each, writes the rules block into `AGENTS.md` and creates `CLAUDE.md` with `@AGENTS.md` when there is none (see "Rules"), then `next: /project-init` |
| `solo-sdd status` | Shows the state of every copy |
| `solo-sdd update [--replace-foreign]` | Repeats the deployment, hints how to update the package; `--replace-foreign` as for `install` |
| `solo-sdd doctor` | Checks the environment: python, copies, hooks, the process guard, `sandbox read`, subagent depth, one `agent <name>` line per chosen agent, `project-agents` when the project's `agents` setting names an agent not installed, `gh`, the `AGENTS.md` keywords in the current folder (`warn agents:` for the old, pre-English ones), the `integration` rows, the size of the project's Codex instructions in the current folder against `project_doc_max_bytes` (`rules-size`: `warn` from 80%, `fail` over the limit, files by descending bytes, the global file separately, outside the budget) |
| `solo-sdd migrate-agents [folder] [--write]` | Renames the old `AGENTS.md` headers and items to English (`## Working copy`, `## Delivery`, `## Commands` and their items): without `--write` it prints a diff, with `--write` it edits the file; the rest of the text does not change, a repeated run changes nothing |
| `solo-sdd uninstall [--purge \| --global-rules]` | Removes copies of every agent and hooks; `--purge` also removes `~/.local/share/solo-sdd` and a `solo` schema an earlier version built; `--global-rules` removes only the global rules block and turns it off for later installs |
| `solo-sdd validate [<id>] [--all] [--json]` | Checks the `solo-sdd/` process tree without any external program: `project.md`, the main specs and the open changes (the archive is history and is not checked), or one change by `<id>` |
| `solo-sdd list [--specs] [--json]` | Prints the open changes of the `solo-sdd/` tree, one line each: the id, done and total tasks, `CLAIM` or `WAITING` if the folder has that file; with `--specs` the main specs with their requirement count; with `--json` the same as a list of objects; archived changes are not listed |
| `solo-sdd new <id>` | Creates `solo-sdd/changes/<id>/` with `proposal.md`, `verification.md` and `tasks.md` from `templates/solo-sdd/change/` and prints their paths and the path of the delta spec template; refuses an id that is not kebab-case, the reserved `archive`, or an id that an open or archived change already has |
| `solo-sdd archive <id> [--yes] [--force]` | Validates the change, refuses an unticked task before the last group of `tasks.md` or an empty `## Result` (`--force` is the owner's: it archives anyway and prints `forced: <what was open>`; agents never pass it), applies its deltas to the main specs (`RENAMED`, `REMOVED`, `MODIFIED` replaces the whole block, `ADDED` appends; a new capability gets a main spec with the delta's `## Purpose`) and moves the folder to `changes/archive/YYYY-MM-DD-<id>/` |
| `solo-sdd config list\|get <key>\|set <key> <value>\|unset <key>` | Reads and changes the project settings in `solo-sdd/config`, see [Settings](#settings) |
| `solo-sdd integrations list\|enable <name>\|disable <name>` | Lists the found integrations with their source and state, turns one on or off, see [Integrations](#integrations) |
| `solo-sdd check --point checks\|ship [--changed] [--change <id>]` | Runs the enabled integrations of the point and records the result by the working tree; `--change` writes the line into the change's `verification.md`, see [Integrations](#integrations) |
| `solo-sdd check --point review\|audit [--changed] [--tag <tag>]` | Runs nothing and lists the material files of the enabled integrations of the point, with `--tag` those with the tag, see [Integrations](#integrations) |
| `solo-sdd import openspec [folder] [--write]` | Converts an `openspec/` tree into `solo-sdd/`: without `--write` prints the plan, with it creates the tree; see [below](#moving-from-openspec) |
| `solo-sdd sync pull <name> [--from <place>]` | Pulls an edit made in place into the repository |
| `solo-sdd --version` | Prints the version |

More of what the commands above do:

- `solo-sdd install`: removes the copies of `openspec-after-update.py`, its test and the `templates/openspec/` files an earlier version deployed when unchanged (an edited one is kept and named) and names `~/Library/LaunchAgents/local.openspec-after-update.plist` if it is there, for you to unload and delete; with `--hooks` connects the hooks in `~/.claude/settings.json` (only with `claude` among the agents); `--replace-foreign` replaces files solo-sdd did not lay out, see [Updating the deployment](#updating-the-deployment)
- `solo-sdd init`: an existing file is never changed except for the solo-sdd block in `AGENTS.md`, a repeat creates nothing; a project with `openspec/` and no `solo-sdd/` gets no file, only the hint `solo-sdd import openspec`; the only external programs are `git` and `gh`, read-only
- `solo-sdd validate`: dry-runs each change's deltas against the main specs in memory (after the deltas of the open changes its `Depends On` names), so a name `archive` would refuse is a `delta` error before any code; prints `<file>: <rule>: <item>` per error and `<n> errors`, with `--json` a list of `file`, `rule`, `item`; exit code 1 on any error, `no solo-sdd/ tree` outside a project
- `solo-sdd archive`: an unknown name, an existing `ADDED` name, a failed check or an existing archive folder changes no file; without `--yes` it asks on a terminal and refuses without one; after the archive it prints `sibling: <change> <section> <requirement>` for each open change whose delta modifies, removes or renames a requirement the archive touched

The `solo-sdd/` tree of a project: `project.md` (intent, language, mode), optional `analyze.md`, main specs `specs/<capability>/spec.md`, open changes `changes/<id>/` (`proposal.md`, `verification.md`, `tasks.md`, optional `design.md`, deltas `specs/<capability>/spec.md`; a change without deltas has the line `Specs: none` under `## Capabilities`) and the archive `changes/archive/YYYY-MM-DD-<id>/`.

`validate` enforces the required proposal and verification sections, at most 10 tasks with the last group `Acceptance`, requirement text of at most 500 characters, WHEN/THEN scenario steps, delta sections and `## Purpose` for a new capability. This repository keeps its own process in `solo-sdd/`.

The whole algorithm: [ALGORITHM.md](https://github.com/veraetogrex-portfolio/solo-sdd/blob/main/ALGORITHM.md). The lessons the rules grew from: [LESSONS.md](https://github.com/veraetogrex-portfolio/solo-sdd/blob/main/LESSONS.md). The third-party files the repository ships: [SOURCES.md](https://github.com/veraetogrex-portfolio/solo-sdd/blob/main/SOURCES.md).

## Updating the deployment

A skill or rules edit goes into the repository, then the deployment:

```bash
cd solo-sdd
python3 sync.py status
python3 sync.py push
```

`push` does not overwrite a copy edited in place after the last deployment (for example, Codex added to a skill right in `~/.codex/skills`). Such a copy is marked `drift` and skipped. To pull the edit into the repository:

```bash
cd solo-sdd
python3 sync.py pull spec-next
git diff
python3 sync.py push
```

If copies in different folders were edited differently, `pull` asks for the source: `--from ~/.codex/skills`. `push --force` overwrites edits in place too. Before any overwrite the previous text is saved to `~/.local/share/solo-sdd/backup/`.

A whole file at a target path that solo-sdd did not lay out (`status` shows `first`, for example another tool's `~/.claude/skills/ship/SKILL.md`) is kept: `install`, `update` and `push` print `foreign <path>: kept (install --replace-foreign replaces it)`, lay out the rest and exit with code 1; `--replace-foreign` on any of the three saves it to a backup and replaces it, the other files of its folder stay. A file equal to its source is adopted as `ok`.

A rules file (`~/AGENTS.md`, `~/.codex/AGENTS.md`, `~/.claude/CLAUDE.md`) keeps its text and gets the block. A run that writes a backup keeps the 20 newest run folders of `backup/` (by the time in the folder name, then by modification time; a folder named by the time alone is one an earlier version wrote), deletes the older ones and prints `pruned backups: <n>`; an entry with another name stays.

`state.json` is written through a new file and an atomic replace; a `state.json` that cannot be read, does not parse or is not a JSON object stops `status`, `install`, `update`, `uninstall`, `sync pull`, `doctor` and `sync.py` with exit code 1 and `fail state: <path>: <reason>`, before any file changes; a missing one is a fresh deployment.

## Releases

A release is a tag `v<version>` on a `main` commit whose `package.json` and `solo_sdd/__init__.py` hold that version. `.github/workflows/release.yml` runs the tests and `python3 scripts/release_check.py <tag>` (the versions, the sdist, the wheel built from it and the npm tarball, each file tracked by git, a `--version` run of each), then publishes the same files to PyPI and npm through trusted publishing and creates a GitHub release with them.

`CHANGELOG.md` names the changes each version archived; the release check refuses a version without its `## <version>` section, and that section is the text of the GitHub release. The one-time registry setup and the release steps: [docs/release.md](https://github.com/veraetogrex-portfolio/solo-sdd/blob/main/docs/release.md).

## How solo-sdd stops

Two words place solo-sdd. The **harness** is what one agent run sees, may touch and how its result is checked: here it is the project's `AGENTS.md` and the global rules (`global/AGENTS.md`), the change artifacts (`proposal.md`, delta specs, `verification.md`, `tasks.md`), the `CLAIM` and `WAITING` markers, the worktree of a dispatched change, the hooks (`global/work_hooks.py`, `global/process-guard.py`) and the check commands from `AGENTS.md`.

The **loop** is what repeats runs until the goal is met: `spec-next` for one change (task, check, review round, live scenario, archive) and `spec-dispatch` for a wave of changes, one orchestrator per change.

The goal of the loop is not "tests green": a change is done when it is accepted by its spec, an agent that did not write it reviewed it, and its live scenario passed (`ALGORITHM.md`, Principles 4, 7 and 10). A run that does not reach the goal stops by rounds or by proof:

| Stop condition | What happens | Where it is enforced |
|---|---|---|
| One run, one change | The next change is not started | `skills/spec-next/SKILL.md`, step 11 |
| Review: at most three rounds | An open `Important` after the third: the findings and "reconsider the approach" go to `Not Verified`, no archive | `skills/spec-next/SKILL.md`, step 7a; `ALGORITHM.md`, step 5 |
| Reviewer failure | One rerun per round; a second failure in the round: the requirements without a verdict go to `Not Verified`, no archive | `skills/spec-next/SKILL.md`, step 7a; `ALGORITHM.md`, step 5 |
| The same edit did not help twice | Stop and find the cause; no third attempt the same way | `global/AGENTS.md`, section 3; `skills/relay/SKILL.md` |
| A running service: the second edit did not help | Stop and analyse; a third edit the same way is forbidden | `skills/debug-profile/SKILL.md`, "Two failures in a row"; `ALGORITHM.md`, step 6 |
| The live scenario failed, no allowed Fallback | No archive, the status is "not done" | `ALGORITHM.md`, step 7; `skills/spec-next/SKILL.md`, step 9 |
| Open CRITICAL or HIGH findings of `spec-analyze`, or a dependency from `Depends On` not archived | The change is not ready, `spec-next` takes another; under the dispatcher an unarchived dependency gives `not_ready` | `ALGORITHM.md`, gate G2; `skills/spec-analyze/SKILL.md`; `skills/spec-next/SKILL.md`, step 4a and "Under the dispatcher" |
| The change has another agent's `CLAIM` or a `WAITING` | The change is not taken; the hook refuses edits to it | `ALGORITHM.md`, step 5; `skills/spec-next/SKILL.md`, step 2; `global/AGENTS.md`, section 9; `global/work_hooks.py`, `guard` |
| The dispatcher's worktree misses something | `blocked` with what is missing | `skills/spec-next/SKILL.md`, "Under the dispatcher" |
| The session ends with work left | The `stop` hook returns the agent once while there are uncommitted edits, a ready change not archived, an open unmerged PR, an interface not checked in a browser or a reply in the wrong language; the `guard` hook refuses an `archived` status whose commit, archive or `CLAIM` do not match | `global/work_hooks.py`, `stop` and `guard` |
| Interface Hard Gate FAIL | One fix and one repeat of the check; a FAIL after it stays in the report, the interface is not ready | `skills/ui-check/SKILL.md`, step 8 and "Gate" |
| A codebase map file missing or empty | Its subagent runs once more; then the file is reported as not written | `skills/project-init/SKILL.md`, step 4a |
| A change grows past 10 tasks | It becomes several changes linked through `Depends On` | `ALGORITHM.md`, Principle 2 |
| Orchestrators at once | At most the "Orchestrators:" limit, 2 by default | `global/sdd_dispatch_plan.py` |
| Subagent depth below 2 | The dispatcher launches nobody | `skills/spec-dispatch/SKILL.md`, step 1 |
| An orchestrator status does not match the checks | One return to the orchestrator, a repeat means "not ready"; `not_ready` and `blocked` continue only by the owner's decision | `skills/spec-dispatch/SKILL.md`, step 6 |
| The dispatcher's returns | One return for a conflict (another for a conflict in other files), a red check, CodeQL alerts or a build failure after update, one CI rerun for `infra`, one repeat of `land`; a repeat ends as "not merged" with the reason | `skills/spec-dispatch/SKILL.md`, step 7 |
| Main is red after a merge, the main folder is not clean, or the branch touches an owner-only path | No new launches or merges and a question to the owner; "not merged"; the change waits for the owner | `skills/spec-dispatch/SKILL.md`, step 7 |
| The CI wait | A failed check that is not a test, no checks at all for 180 s, a required check that has not started for 300 s, or the whole wait over 1200 s gives `infra` | `global/sdd_pr.py` |
| A paid call, deleting or overwriting data, an action on prod | Stop and ask, naming what happens, how many calls and the amount | `ALGORITHM.md`, Principle 5; `global/AGENTS.md`, section 2; `skills/ship/SKILL.md`, step 2 |
| A secret in the diff | Stop and say so | `skills/ship/SKILL.md`, step 4 |
| A blocker without a workaround | What is unchecked goes to `verification.md` and `docs/waiting.md`, the rest gets closed | `ALGORITHM.md`, Principle 6; `global/AGENTS.md`, section 4 |
| `agent-quality` | Names the stop condition and the cost before a paid run | `skills/agent-quality/SKILL.md`, step 6 |

The other side of the same rules: the agent does not stop while there are unfinished items and no real blocker (`global/AGENTS.md`, section 2), and an orchestrator does not end its turn while its subagent or background command runs (`skills/spec-next/SKILL.md`, "Under the dispatcher").

There is no token budget, on purpose: the limits are counted in rounds and proofs, and the cost is held by the cheapest models in tests and by consent before every paid run (`ALGORITHM.md`, Principle 9).

## Claude Code workflow hooks

The hooks close the most frequent repeats in work with an agent: reading the project rules, continuing, archiving, merging, status. One script `global/work_hooks.py`, subcommands:

| Subcommand | Event | What it does |
|---|---|---|
| `context` | SessionStart | Puts into the context AGENTS.md (unless CLAUDE.md imports it with `@AGENTS.md`), `solo-sdd/project.md` (`openspec/config.yaml` in a project still on `openspec/`), `docs/status.md`, the branch, `git status`, changes with progress and CLAIM/WAITING markers; a `hook errors: <n> in the last 7 days, last: <line>` line when `errors.log` has entries of the last 7 days, also outside a project; an `integration errors:` line, see [Integrations](#integrations) |
| `guard` | PreToolUse | Catches direct reads of a `.env` file and the rest of the list under the table |
| `subagent-context` | SubagentStart | Gives a subagent the path to the main folder's `AGENTS.md` and the open changes with CLAIM/WAITING markers, no longer than 4000 chars |
| `stop` | Stop | While the session has `running` background tasks, it stays silent. Otherwise it returns the agent once if there are uncommitted edits of this session, a ready change not archived, an open unmerged PR, an interface not checked in a browser (a check by any subagent of the session counts, by its transcript in `<id>/subagents/`), an edit in a `checks` integration's `applies` not run on this tree, or a final answer not in the language of `reply.language` in the project's `solo-sdd/config`, else of `SOLO_SDD_REPLY_LANG` (`ru` or `en`; with neither set the language is not checked) |
| `beat`, `status` | all events, status line | The current action, time, number of subagents |
| `end` | SessionEnd | Removes the CLAIMs the hook placed; keeps the last 1000 lines of `errors.log` |

`guard` catches:

- direct reads of a `.env` file (`.env`, `<name>.env`, `.env.<suffix>` in any letter case, dots allowed: `.env.development.local`; exactly `.env.example`, `.sample`, `.template`, `.dist` pass; a folder named `.env` is not the file):
  - `Read` of it, `Grep` with it as `path` or a `glob` that matches `.env` itself (`.e*`, `*`), a `.env` name it spells out (`**/.env.production`) or a `.env` file under the search folder (a `Grep` over a folder without such a glob passes),
  - and in Bash a `.env` path given to any program (also inside `python3 -c`, `bash -c`, `eval`, nested substitutions and `echo … | sh`), an input redirect from it, `source` or `.` of it, a copy, link or move of it, `find -exec` on it;

  `ls`, `test`, `[`, `stat`, `touch`, `chmod`, `echo`, `printf`, `git check-ignore`, `find` by its name, a copy into it (`cp .env.example .env`, plain flags only), `grep`/`rg` with a flag that prints only counts or names (`-c`, `-q`, `-l`) and `>>` into it pass. Options, shell flags and redirections are read by each program's grammar (clustered and glued values, `--`, quoted `<` and `>` are text); an option it does not know drops the exemption.

  These exemptions hold only in a plain command: one with `#`, `$'`, `${`, `$(`, a backquote or a backslash is refused when it names a `.env` file or holds `env`, `printenv` or a bare `set`/`export`/`declare` anywhere, comments and quoted text included (`echo hi # see .env` is refused). The Bash checks are a guard against the agent's accidental reads, not a boundary; known bypasses: brace expansion (`cat .e{n,}v`), `sh -c` with the file as a positional argument, process substitution with a quoted `)`, a heredoc marker line with an open quote, `${X:-env}`, BSD `sed r` without a space.

  The boundary is `Read(**/.env)` in `permissions.deny` and secrets kept only in `.env`. It does not see a program that opens the file itself (`python3 script.py`, a heredoc body for an interpreter, a name built at run time).

  With the Claude Code sandbox on (`sandbox.enabled` in `~/.claude/settings.json`, which solo-sdd never turns on), Claude Code also applies `Read(...)` deny rules to sandboxed Bash commands, so on macOS the same rule is expected to cover them; `sandbox.filesystem.denyRead` takes only absolute and `~` paths and cannot name `.env` in every project, and on Linux the sandbox ignores glob `Read` rules (read from the Claude Code 2.1.312 binary; no sandboxed session was run).

  `install --hooks` ends with a `sandbox read deny:` line: `expected active` (not proven in a session), `off, it needs the sandbox`, or `not active` or `unknown` with the reason; `doctor` prints the same as `sandbox read`, `warn` only when the sandbox is on and the deny does not apply.

- Dumps of the environment (`env`, `printenv`, bare `set`, `export -p`, `declare -p`) and `echo`, `printf`, `printenv` of a secret variable: one part of the name, split at `_`, digits and camelCase, is `KEY`, `TOKEN`, `SECRET`, `PASSWORD`, `PASSWD`, `WEBHOOK` or `CREDENTIAL` (with a trailing `S` too), so `$API_KEY` and `$apiKey` are refused and `$MONKEY_NAME` passes.
- Overwriting `.env`, a second `.env`, `git add` of secrets;
- subagent models by the role tag at the start of `description` (`model-policy.json`: `Review:` is review, `Orchestrator` is the orchestrator, `Implement:` is an executor; words without a tag do not set a role): acceptance and review run without `model` or on a model from the `main` list (the main model), the orchestrator only from the main session, an executor never from a subagent (the orchestrator writes the change code);
- expensive models in Bash tests (`-m`, `model=`), and with `--model` any model outside the `cheap` list; the owner allows a bypass through `SOLO_SDD_EXPENSIVE_OK=1` in the environment, and writing this variable into settings and the shell profile is forbidden to the agent;
- editing another session's change by CLAIM and a change with WAITING;
- a worktree outside the temporary folder, except the built-in Claude Code worktrees (`claude --worktree`, `EnterWorktree`, `isolation: worktree` of a subagent pass); `codex --worktree` is refused, and `git worktree add` passes only as a command of its own in the plain form `git worktree add [-b <name> | -B <name> | --detach | -f] <path> [<commit>]` under a temporary folder: `git -C`, `-c`, a wrapper, a quoted or variable subcommand and a path that a `TMPDIR` change, an `ln` or a `cd` earlier on the line can move are refused (a guard against accidents, not a boundary);
- the first write outside the project;
- in a project with a `solo-sdd/` tree (the git root of the session folder), `gh pr merge` and a `gh api` call to `pulls/<n>/merge` (also after `&&`, inside `bash -c`, `eval` or a substitution; a quoted message or a search pattern is text), naming `sdd-pr.py merge`, whose gates a direct merge skips (a guard against an accidental direct merge by the plain forms, not a boundary; branch protection is the boundary).
  Known bypasses that pass: `xargs`, `find -exec`, `sudo -u`, `env -u`, a shell function, `bash -c`, `eval` or a quoted assignment after `A=(…)` or in `=(…)`, substitutions nested deeper than 3 or cut early by a quoted `(` or `)`,
  a quote inside a word after `A=(…)` or in `=(…)` (`A=(1 2) 'g'h pr merge 5`);
- the same heredoc body and search pattern rules as in `process-guard`, in the secret and model checks in Bash;
- an orchestrator status handback (`SubagentHandback` with a `STATUS:` block; the exit code in `VALIDATE` and `TESTS` allows a note: `-> exit 0 (250 tests)`), if the fields, the `HEAD` commit, the change archive or the removed CLAIM do not match git and the files.

An internal error lets the action through and is written to `~/.claude/hook-state/errors.log`; the `context` line above and `doctor` (`warn hook errors`) name the entries of the last 7 days.

A broken `model-policy.json` lets through only the checks that read it (models, `Agent` roles, the archive review gate; the `stop` browser check keeps only its built-in signs), every other check runs, and `doctor` prints `fail model policy: <reason>`.

`model-policy.json` is yours to edit in the deployed copy `~/.claude/hooks/model-policy.json`:

- the model lists (`cheap`, `expensive_always`, `expensive`, `main`);
- the `browser` key: `tools` (tool name prefixes), `skills` (skill names) and `bash` (plain substrings of a Bash command) add to the built-in signs the `stop` interface check counts as a browser check; an edit cannot remove a built-in sign, and a part that is not a list of non-empty strings adds nothing and writes an `errors.log` line naming it.

`install`, `update` and `sync.py push` keep an edited copy: they print `skipped    global/model-policy.json               ~/.claude/hooks/model-policy.json — edited in place: ...` and `sync.py status` shows it as `drift`. While it is `drift`, a newer shipped model list is not taken. To take it from a clone, `python3 sync.py push --force` overwrites the copy and prints `updated ... (saved: ~/.local/share/solo-sdd/backup/<run>/.claude/hooks/model-policy.json)`; from the package, move the copy aside, run `solo-sdd update` (it prints `created` for the shipped copy) and carry your edits over.

## Claude Code process protection

`sync.py push` puts the hook `global/process-guard.py` into `~/.claude/hooks/`. `solo-sdd install --hooks` (and `work_hooks_settings.py`) connects it in `~/.claude/settings.json`: a PreToolUse hook on `Bash|Monitor` and `permissions.deny` rules `Bash(<name> *)` for `pkill`, `killall`, `kill`, `osascript`, `launchctl`, `shutdown`, and `Read(**/.env)`, which keeps the `Read` tool off `.env` when the `guard` hook fails open (it claims nothing about `Grep` or Bash); an entry or a rule already there, connected by hand, is kept and not recorded, and `uninstall` removes only what install added.

`doctor` prints `ok process guard: connected` or `warn process guard: not connected`. The hook command: `exec /usr/bin/python3 "$HOME/.claude/hooks/process-guard.py"`, `timeout: 5`, `onFailure: "block"`.

The hook checks the command text, including usual wrappers and substitutions:

- a heredoc body that does not go to a shell (`cat > f <<'EOF'`, `python3 - <<'EOF'`), a `grep`/`rg`/`git grep`/`ag` search pattern, the message of `git commit`/`git tag` (`-m`, `--message`) and of `gh pr`/`gh issue` (`-t`, `--title`, `-b`, `--body`) and a name followed by `.` or `/` in a file path (`docs/kill.md`) do not count as a command;
- a name run as a program, by its path (`/bin/kill`), in `bash -c` or in a substitution, also inside a message, is still checked, and so is everything when `$'…'`, `${ …; }`, zsh `=(…)` or a word starting with `#` stands anywhere on the line (the shell reads their quotes differently or runs a command there; an array assignment `A=(x y)` counts too), while a body for any other receiver (a shell, a shell behind a wrapper, an unknown program, including through `|`) is checked;
- it does not analyse the content of launched programs or computed names.

This is protection against accidental direct commands, not OS-level process isolation.

## Checks

```bash
cd solo-sdd
python3 -m pip install --user hypothesis
python3 tests/run.py --tier slow < /dev/null
python3 -m solo_sdd validate --all
```

A round of checks while coding runs `python3 tests/run.py --tier fast`, then `python3 tests/run.py --affected <path>...`; the run before a release tag is `python3 tests/run.py --tier release`. The marks are in `tests/marks.py`; a direct `python3 tests/<file>.py` runs every test of the file.

The scripts in `global/` are deployed one file each, so some code blocks live in several `.py` files between the lines `# <name>:begin` and `# <name>:end`. A shared block is edited only in its source file (the `SOURCES` table of `scripts/sync_blocks.py`), then `python3 scripts/sync_blocks.py` copies it into every other file with those markers and names each rewritten copy; `--check` writes nothing and names each stale copy, and the copy tests run it.

A begin without its end, an end without its begin, a block twice in a file, a name without a source, a scanned folder it cannot list, a link to a folder or a `.py` file, a file with a lone CR line break or a copy it cannot write stops the script with code 1 before any write.

## What is not here

- Skills of a specific project live in that project.
- Skills unrelated to development stay in the agent folders, `sync.py` does not touch them.
