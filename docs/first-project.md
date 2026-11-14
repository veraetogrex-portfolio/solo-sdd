# Installation, first project and rules

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
