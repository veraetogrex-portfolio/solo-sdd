# solo-sdd

solo-sdd is a spec-driven development process for AI coding agents: a change counts as done only after a live check and a review by an agent that did not write it. It works for one person or a team, with Claude Code, Codex or any agent that reads `AGENTS.md`.

[![PyPI](https://img.shields.io/pypi/v/solo-sdd)](https://pypi.org/project/solo-sdd/) [![npm](https://img.shields.io/npm/v/solo-sdd)](https://www.npmjs.com/package/solo-sdd) [![Tests](https://github.com/veraetogrex-portfolio/solo-sdd/actions/workflows/test.yml/badge.svg)](https://github.com/veraetogrex-portfolio/solo-sdd/actions/workflows/test.yml) [![License: MIT](https://img.shields.io/badge/license-MIT-blue)](https://github.com/veraetogrex-portfolio/solo-sdd/blob/main/LICENSE)

## Quick start

You need Python 3.9+, git and a coding agent.

```bash
pip install solo-sdd
solo-sdd install --hooks
cd ~/code/my-project
solo-sdd init
```

`solo-sdd install` puts the skills into the agent folders of your home; `--hooks` connects the Claude Code hooks that enforce the rules (with Codex alone, run it without `--hooks`). `solo-sdd init` sets up the process in the project's git repository: three questions, Enter accepts each proposal. Then, inside the project, in the agent:

1. `/project-init`: the project rules in `AGENTS.md` and `.env.example`.
2. `/spec-plan` with a plan, a bug list or an idea: a queue of small changes in `solo-sdd/changes/`.
3. `/spec-next`: one change from selection to archive: code, tests, a live check, a review by another agent, delivery.

To see one full cycle before your own code, run the demo: [examples/demo/WALKTHROUGH.md](https://github.com/veraetogrex-portfolio/solo-sdd/blob/main/examples/demo/WALKTHROUGH.md), about five minutes.

## One change, start to finish

A change is a folder. This is the demo's `split-bill`, which adds `--people` to a tip calculator:

```
solo-sdd/changes/split-bill/
├── proposal.md       why, what changes, what is out of scope
├── specs/tip/spec.md the new requirement and its scenarios
├── verification.md   the live scenario, written before the code
└── tasks.md          at most 10 tasks, each with its proof
```

<details>
<summary>The requirement in <code>specs/tip/spec.md</code>, shortened</summary>

```markdown
### Requirement: Split between people
With `--people <n>`, `tip.py` SHALL print a second line `each <share>`, where
the share is the total divided by `n` and rounded up to a cent.

#### Scenario: Four people
- **WHEN** the user runs `python3 tip.py 40 15 --people 4`
- **THEN** it prints `tip 6.00, total 46.00` and then `each 11.50`
```

</details>

`/spec-next split-bill` then runs without questions:

1. Checks the change against itself and the main specs before any code.
2. Writes a failing test for each scenario, then the code.
3. Runs the whole suite and the live scenario: `python3 tip.py 40 15 --people 4` must print `each 11.50`.
4. Hands the diff to another agent, which accepts it requirement by requirement.
5. Archives the change: its requirement moves into `solo-sdd/specs/tip/spec.md`, and the work is committed.

## Why

- An agent reports success once the unit tests pass. solo-sdd closes a change only after its live scenario passed on real input and another agent accepted it requirement by requirement.
- Requirements live next to the code. Every change carries its own delta, and archiving the change applies it to the specs.
- A change has at most 10 tasks; a larger plan becomes a queue of changes with explicit dependencies.
- The agent records each decision in the change instead of asking, and stops only before paid calls, deleting data or an action on prod.
- In Claude Code, hooks refuse a premature "done", the wrong model for a review and edits to a change another session took.
- In `solo` mode changes merge locally; in `team` mode they go through pull requests that a person merges. Ready changes can run in parallel, one agent per change.

## Skills

| Stage | Skills |
|---|---|
| Plan | `/project-init` prepares a project, `/spec-plan` turns a plan into changes, `/spec-analyze` checks a change before code |
| Build | `/spec-next` takes one change to the archive, `/spec-dispatch` runs ready changes in parallel, `/codex-orchestration` hands units to Codex |
| Check | `/spec-audit` code against the spec, `/ui-check` an interface against the mockup, `/copy-check` product texts, `/debug-profile` a failing service or bug, `/agent-quality` an AI agent's answers |
| Deliver | `/ship` commit, push, pull request, merge |
| Status | `/work-status` five lines on the state, `/context-resume` the context after a pause, `/evidence-research` a choice on checked facts |
| Manual | `/relay` another agent's report, `/blockers` blockers into changes, `/report` a summary for a period, `/health` the project's integrations, `/changes` a table of change states |

## Requirements

- Python 3.9+, git; Node 20+ only for the solo-sdd npm wrapper.
- Claude Code, Codex or another agent that reads `AGENTS.md`, see [Supported agents](#supported-agents).

Some skills use extra tools (all optional, needed only for their own skill):

- `gh` (GitHub CLI): `pr` mode of `spec-dispatch` and `sdd_pr.py`, PRs in `ship`;
- `codex` (Codex CLI): `codex-orchestration`;
- a browser for automation: `ui-check`;
- a style skill for a language other than English: that language in `copy-check`;
- `docker compose`: `health` and `debug-profile`, if the project runs through it;

## Installation

```bash
pip install solo-sdd
uv tool install solo-sdd
pipx install solo-sdd
npm i -g solo-sdd
```

Any one of them. The npm package is a wrapper over the same Python code and needs Python 3.9+ in `PATH`. The unreleased `main`: `pip install git+https://github.com/veraetogrex-portfolio/solo-sdd`. From a clone: `git clone https://github.com/veraetogrex-portfolio/solo-sdd`, then `python3 sync.py push` in it. Where the files go: [docs/layout.md](https://github.com/veraetogrex-portfolio/solo-sdd/blob/main/docs/layout.md).

## Supported agents

- Claude Code: rules, skills, hooks and subagents, everything solo-sdd has.
- Codex: rules, skills and subagents; hooks are not verified.
- Any other agent that reads `AGENTS.md`: rules and skills.

The full table with probed versions: [docs/agents.md](https://github.com/veraetogrex-portfolio/solo-sdd/blob/main/docs/agents.md).

## How it stops

There is no token budget: a run stops by rounds and proofs.

- one run takes one change;
- at most three review rounds by default, then the findings go to "not verified" and the change is not archived;
- the same edit failed twice: stop and find the cause;
- a failed live scenario means "not done";
- a paid call, deleting data or an action on prod: stop and ask.

Every condition with the file that enforces it: [docs/stop-conditions.md](https://github.com/veraetogrex-portfolio/solo-sdd/blob/main/docs/stop-conditions.md).

## Update and uninstall

```bash
pip install -U solo-sdd
solo-sdd update
```

`solo-sdd init` in a project refreshes its rules block. `solo-sdd doctor` checks the environment when something does not work. To remove the copies and hooks from your home folder (`--purge` also removes solo-sdd's data folder; the projects keep their `solo-sdd/` trees):

```bash
solo-sdd uninstall
pip uninstall solo-sdd
```

## Docs

- [Installation, first project and rules](https://github.com/veraetogrex-portfolio/solo-sdd/blob/main/docs/first-project.md): every install option, the `init` questions and flags, the rules block
- [Commands](https://github.com/veraetogrex-portfolio/solo-sdd/blob/main/docs/cli.md) and the `solo-sdd/` tree
- [Settings](https://github.com/veraetogrex-portfolio/solo-sdd/blob/main/docs/settings.md) and checklists
- [Integrations](https://github.com/veraetogrex-portfolio/solo-sdd/blob/main/docs/integrations.md)
- [Claude Code hooks](https://github.com/veraetogrex-portfolio/solo-sdd/blob/main/docs/hooks.md) and process protection
- [Stop conditions](https://github.com/veraetogrex-portfolio/solo-sdd/blob/main/docs/stop-conditions.md)
- [Supported agents](https://github.com/veraetogrex-portfolio/solo-sdd/blob/main/docs/agents.md)
- [What goes where](https://github.com/veraetogrex-portfolio/solo-sdd/blob/main/docs/layout.md)
- [Moving from an `openspec/` tree](https://github.com/veraetogrex-portfolio/solo-sdd/blob/main/docs/migrate.md)
- [Developing solo-sdd](https://github.com/veraetogrex-portfolio/solo-sdd/blob/main/docs/development.md) and [releases](https://github.com/veraetogrex-portfolio/solo-sdd/blob/main/docs/release.md)
- [The whole algorithm](https://github.com/veraetogrex-portfolio/solo-sdd/blob/main/ALGORITHM.md), [the lessons it grew from](https://github.com/veraetogrex-portfolio/solo-sdd/blob/main/LESSONS.md), [third-party files](https://github.com/veraetogrex-portfolio/solo-sdd/blob/main/SOURCES.md)

## Contributing

What each version changed is in [CHANGELOG.md](https://github.com/veraetogrex-portfolio/solo-sdd/blob/main/CHANGELOG.md). Bugs and ideas go to [issues](https://github.com/veraetogrex-portfolio/solo-sdd/issues); how to propose a change: [CONTRIBUTING.md](https://github.com/veraetogrex-portfolio/solo-sdd/blob/main/CONTRIBUTING.md).

## License

MIT, see [LICENSE](https://github.com/veraetogrex-portfolio/solo-sdd/blob/main/LICENSE).
