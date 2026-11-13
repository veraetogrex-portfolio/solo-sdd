# sdd-eval: replaying changes and comparing dispatcher configurations

The tool `sdd-eval.py` (`global/sdd_eval.py`) replays a project's archived changes on clean copies and compares `spec-dispatch` configurations by completion, time and cost on one set.

## Workflow

0. Run from the root of the solo-sdd repository or pass `--prices <path>`: `prices.json` is not deployed to agent folders; without it `compare` and `metrics` will not find prices (`compare` prints `price file not found`, time and cost become `n/a`).
1. `sdd-eval.py setup <set.json> --config <configuration.json> --out <E>/a`: project copies on the base of each change (the first parent of the oracle commit), with the current rules and specs. For the second configuration: the same set, another configuration, `--out <E>/b`.
2. `sdd-eval.py run <E>/a --label a1`: `spec-dispatch` on each copy; log `<E>/a/runs/a1.json`. At least two runs per configuration are needed (run the second label on new copies in a neighbouring folder, for example `<E>/a2`).
3. `sdd-eval.py metrics <E>/a --label a1`: time, cost, roles from the session log; writes `runs/a1.metrics.json`. `metrics --session <id>` does the same for one session.
4. `sdd-eval.py compare <E> --a a1 a2 --b b1 b2 [--timeout 1800] [--prices …]`: a markdown report. The label log is looked up in `<E>/runs/`, then in `<E>/*/runs/`. Code 2: fewer than two labels for a configuration or no log; code 3: a copy has no test command.

## Questions to the owner

`claude -p` does not show a question window, so `run` always adds `--append-system-prompt`: a ban on asking the owner and lines `- <question> → <answer>` from the set field `answers` (an object "question → answer", strings; `setup` writes it into the copy's `.sdd-eval`). Answers of the working set: abandoned markers: `Remove and launch`, a spec instead of a change: `Ignore`, other unknown dependencies: `Keep`, delivery mode: `local` (copies have no remote). Dependencies from `Depends On` are parsed as in `sdd-dispatch-plan.py`; archived ones are copied into the copy, a missing one gives the line `dependency not archived` on `setup`.

If the copy's session log has an `AskUserQuestion` call or a "Needs from you" line with a question (not "nothing" and not "none"), the copy's entry in the run log gets `question: "question: <text>"` (up to 300 chars), and `run` prints it after the status. `compare` puts `(question)` next to the cell outcome, lists the change in the `With a question:` section and does not count it as flipped; whether it is done is decided by merge and the oracle.

Layout: `<E>/a/<id>`, `<E>/b/<id>` are copies, `<E>/a/runs/`, `<E>/b/runs/` are logs.

Files: set `tests/eval/sets/*.json` (project, at least 8 changes with an oracle commit, `tests`, `prepare`; a set of a specific project names it and is not in git, `AGENTS.md` section "Working copy"), configuration `tests/eval/configs/*.json` (name and lines of the "Working copy" section), prices `tests/eval/prices.json`, fixtures `tests/eval/fixtures/`.

## Oracle

The oracle is the commit where the change was implemented together with tests. `compare` takes the oracle's test files, lays them over the run result (the last commit of the copy's main branch) in a temporary worktree and runs the test command from the `Tests` row of the "Commands" section of the copy's `AGENTS.md`. A missing file, module or export makes the test runner fail; that is red, not a skip. Done = merged and the oracle is green. The oracle worktree gets links to the ignored `prepare` results of the copy; the test command must be one command without chains.

The set field `oracle_prepare` (optional, a string) runs in this worktree after the test files are laid over and before the tests. Why: `prepare` results that depend on the change code (for example a native helper built on the base) are outdated after merge; `oracle_prepare` rebuilds them. The rebuild goes through links to the copy's folders and writes into the copy, which is acceptable. Non-zero or a timeout means the change is not done, with `oracle_prepare: code N` among the failures.

`merged, oracle red` does not mean the code is wrong: a test could fail because of a different message text or name. The reviewer gives the verdict, not the script.

## Counting method

- One API call is one `message.id`; the log has several lines for it, the maximum of each counter is taken.
- Model output is taken from `cost-state`: the log understates it (run 4: Opus 191 485 in the log versus 1 005 077 in `cost-state`). Output by role is only from the log, a lower bound.
- `input_total` includes the cache (input, cache write and cache read).
- Roles (orchestrator, executor, reviewer, other) and `dispatcher` are counted separately.
- Prices come from `prices.json`; for a message with input above the `long` threshold the `long` rate applies. The `cost-state` output remainder above the log is counted at the model's top rate.
- Time: from the first orchestrator launch to the last merge (in `metrics <folder>`, to the time of the last commit of the copy's main branch).
- `returns` are dispatcher messages (`SendMessage`), `refused` are statuses the hook did not accept. `merged` is the number of merges in the dispatcher log (PR, `land-local`, `git merge`).

## Check against the run 4 analysis

Source: the dispatcher log of run 4 of a consumer project (the id is in the change's `verification.md`). Status: confirmed by this tool, 2026-11-04.

| Metric | Analysis | `metrics --session` |
|---|---|---|
| Merged | 33 | 33 |
| Time | 9.1 h | 9.13 h |
| Opus orchestrators, per change | 5.2M | 5.15M |
| Sonnet executors, per change | 1.0M | 1.03M |
| Haiku reviewers, per change | 1.5M | 1.48M |
| Cost | $136.55 (`cost-state`) | $137.21 (`prices.json`, +0.5%) |

The analysis counted Opus without the dispatcher session (2.82M per change), so do not compare "all Opus" totals with it.

## Limitations

- A copy gets the current specs and documents of the main folder (the leak is the same for all configurations).
- A project where `AGENTS.md` or `openspec/` are tracked by git is not supported: the copy comes out dirty and the dispatcher refuses to merge (this does not affect the working set, where they are ignored).
- `MODIFIED` of a requirement that changed later does not pass `openspec validate --strict` in the copy, with the error `omits scenario(s)` (one change of the working set); the orchestrator fixes the delta itself, this work is the same for all configurations and is part of the comparison.
- `run` does not set the permission mode or a deadline.
- Prices from the claude-api table of 2026-10-06; Sonnet 5.5 and Haiku 5.5 corrected by the actual values.

## Baseline

Not taken: it needs two runs of the set with the owner's consent.
