# Demo: one change in five minutes

`tip` is a tiny command-line tip calculator with its solo-sdd tree: one main spec (`solo-sdd/specs/tip/`), one archived change (`tip-calc`, the first version of the command) and one open change, `split-bill`, that adds `--people`. You run the open change through `/spec-next` and see what solo-sdd leaves behind.

You need solo-sdd installed (`pip install` and `solo-sdd install` from the [quick start](../../README.md#quick-start)), git with your name and email set, Python 3.9+ and Claude Code or Codex.

## 1. Get the demo

```bash
git clone --depth 1 https://github.com/veraetogrex-portfolio/solo-sdd ~/solo-sdd-src
cp -R ~/solo-sdd-src/examples/demo ~/solo-sdd-demo
```

If you already have a clone, copy `examples/demo` from it instead. `~/solo-sdd-demo` must not exist yet.

## 2. Make it a project

```bash
cd ~/solo-sdd-demo
git init -q
solo-sdd init --yes
git add -A
git commit -qm "demo start"
python3 -m unittest discover -s tests
solo-sdd validate --all
solo-sdd list
```

`solo-sdd init --yes` keeps the demo's `solo-sdd/config` (solo mode, local delivery: no remote, no pull request) and `solo-sdd/analyze.md`, adds the solo-sdd rules to `AGENTS.md`, a `CLAUDE.md`, `docs/waiting.md` and `solo-sdd/rules-block`. It ends with `next: /project-init`, the step for a new project: the demo already has its rules, so skip it here. The tests pass, `validate` prints `0 errors`, and `list` prints `split-bill 0/4`: the open change with none of its four tasks done.

Before the agent starts, read the change: `solo-sdd/changes/split-bill/proposal.md` (why and what), `specs/tip/spec.md` (the new requirement and its scenarios), `tasks.md` and `verification.md` (the live scenario that proves it).

## 3. Run the change

Start the agent in `~/solo-sdd-demo` and give it one request:

- Claude Code: `/spec-next split-bill`
- Codex: `implement the change split-bill with the spec-next skill`

The agent works without questions: it checks the change before code, writes the failing tests first, then `--people` in `tip.py`, runs the live scenario from `verification.md`, has another agent review the diff, archives the change and commits it to the local main branch: the demo has no remote, so nothing is pushed. It takes a few minutes.

## 4. What to look at

```bash
cd ~/solo-sdd-demo
solo-sdd list
ls solo-sdd/changes/archive
git log --oneline
python3 -m unittest discover -s tests
solo-sdd validate --all
```

After the run:

- `solo-sdd list` prints no open change, and `solo-sdd/changes/archive/` holds `<date>-split-bill` next to `<date>-tip-calc`.
- `solo-sdd/specs/tip/spec.md` now has the requirement "Split between people": the archive applied the change's delta to the main spec.
- `solo-sdd/changes/archive/<date>-split-bill/verification.md` has a filled Result: what was run and what it printed.
- `git log --oneline` has a commit with the change after `demo start`.
- `python3 tip.py 40 15 --people 4` prints `tip 6.00, total 46.00` and then `each 11.50`.

## 5. Your own project

Delete `~/solo-sdd-demo` and `~/solo-sdd-src` when you are done. For your own code, follow [First project](../../README.md#first-project): `solo-sdd init`, `/project-init`, `/spec-plan` with your plan, then `/spec-next`.
