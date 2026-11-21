# solo-sdd

## Purpose and mode

Own spec-driven development process for one person or a team, with any coding agent, independent of other spec tools: the algorithm, skills, global agent rules, Claude Code hooks and project templates. The repository is the source of truth; `sync.py push` puts the files in place.
Mode: prod. Prod here is the agent folders on this computer (`~/.claude`, `~/.codex`, `~/.agents`, `~/.local/bin`): after `sync.py push` an edit takes effect in all sessions at once.

## Sources of truth

- Behaviour contract: `solo-sdd/specs/`; active work: `solo-sdd/changes/`; the project intent: `solo-sdd/project.md`.
- Algorithm: `ALGORITHM.md`; the lessons the rules grew from: `LESSONS.md`; the full text of each `## Lessons` line is in its section `Lessons of this repository` under the same id, and a refinement edits both.
- `README.md`: what lies where and how it is deployed. `targets.json`: the deployment map.
- Files copied into agent folders are not a source: an edit in place is pulled with `sync.py pull`.
- `solo-sdd/specs/` and the open changes of `solo-sdd/changes/` are kept in git. The change archive `solo-sdd/changes/archive/` and `docs/waiting.md` are not in git, they live only in the working folder: the archive is not published.

## Working with specs

- One change per session, up to the archive.
- No clarifying questions: a reasoned decision, recorded in the report.
- Work outside the current spec becomes a new change.
- After `tasks.md` is closed, an independent live test before reporting readiness.

## Commands

| What | Command |
|---|---|
| Install | Python 3 from the system; for tests and lint, `python3 -m pip install --user hypothesis pyflakes==3.4.0` |
| Tests | `python3 tests/run.py --jobs 5 --tier slow` before delivery; a round: `python3 tests/run.py --jobs 5 --tier fast`, then `python3 tests/run.py --jobs 5 --affected <path>...`; before a release tag: `python3 tests/run.py --jobs 5 --tier release` |
| Tests (one) | `python3 tests/<file>.py`; one test: `python3 -m unittest <module>.<Class>.<test>` from `tests/` |
| Lint | `python3 -m pyflakes solo_sdd global scripts sync.py` |
| CLI | `python3 -m solo_sdd --version` |
| What is deployed and where it differs | `python3 sync.py status` |
| Deployment | `python3 sync.py push` |
| Specs | `python3 -m solo_sdd validate --all` |

## Project map

| Path | Role |
|---|---|
| `skills/<name>/SKILL.md` | Algorithm skills and manual commands; deployed by `targets.json` |
| `skills/<name>/<step>.md` | Step files: the body of a long step moved out of its `SKILL.md` (at most 16,000 bytes), named by the step's line; each has its own `targets.json` entry next to the skill |
| `tests/skill_text.py` | A skill's text joined with its step files, the size budget and the step-file check the tests read |
| `solo_sdd/` | Package and the `solo-sdd` command; deployment logic in `layout.py`, `sync.py` is a wrapper; the `solo-sdd/` tree rules and `validate` in `process_format.py`; `import openspec` in `import_openspec.py`; `init` in `init.py` |
| `pyproject.toml` | Package description |
| `package.json`, `bin/solo-sdd.js` | npm package: a wrapper that runs `python -m solo_sdd` |
| `global/AGENTS.md` | Global rules of both agents |
| `global/work_hooks.py`, `global/model-policy.json` | Claude Code workflow hooks and the model policy |
| `global/work_hooks_settings.py` | One-off connection of the hooks in `~/.claude/settings.json` |
| `global/process-guard.py` | Hook that forbids stopping processes directly |
| `global/sdd_dispatch.py` | Status acceptance and `local` mode merge for `spec-dispatch` |
| `global/sdd_eval.py` | Change replay and comparison of dispatcher configurations |
| `tests/eval/` | Sets, configurations, prices, fixtures |
| `templates/` | Templates for new projects |
| `examples/demo/` | Demo project with its `solo-sdd/` tree and `WALKTHROUGH.md`; kept valid by `tests/test_demo.py` |
| `integrations/antislop/` | Bundled integration `antislop`: pinned copy of the anti-slop rules for `ui-check` and `copy-check` with its `integration` description; deployed by `targets.json`, updated only by replacing the copy |
| `integrations/security-audit/` | Bundled integration `security-audit`: pinned copy of `cloudflare/security-audit-skill` for the security pass of `spec-audit` with its `integration` description; deployed by `targets.json`, updated only by replacing the copy |
| `solo-sdd/` | Specs, changes and the archive of this repository; the archive lives only in the working folder |
| `scripts/publish-first.sh` | First publication: a new `main` without history and without `solo-sdd/`, one-off |
| `scripts/pre-push-guard.sh` | `pre-push` hook the publication step of `docs/release.md` installs: refuses a pushed commit that shares history with `history-local` or `history-private`, and a ref not to a commit |
| `scripts/release_check.py` | Release check: tag against versions, sdist, wheel from the sdist and npm tarball into `dist/`, packed files against `git ls-files`, `--version` smoke, the `CHANGELOG.md` section; `--notes <tag>` prints that section |
| `CHANGELOG.md` | The changes each version archived; its section of the current version is the GitHub release text |
| `.github/workflows/release.yml` | Release on a pushed tag `v<version>`: tests, release check, PyPI and npm through trusted publishing, GitHub release |
| `docs/release.md` | One-time registry setup and the release steps |
| `.github/workflows/test.yml` | CI: lint, `tests/run.py` and `solo-sdd validate --all`; the `slow` tier on Ubuntu for a push or PR, the `release` tier on macOS for a `v*` tag and on both for a manual run; a newer run of a ref cancels the older one |
| `tests/` | Tests and probes; `tests/run.py` runs every `tests/test_*.py` in parallel, failed first (`--failed`, named files, `--affected <path>` by `tests/affected.json`); `tests/stands/` holds live scenario stands |

## Working copy

- Paths: `docs/waiting.md`, `docs/debug-profile.md`, `docs/rules-audit.md`, `docs/process-safety-verification.md`, `global/claude-gui.py`, `global/claude-process-safety-settings.json`, `global/claude-safe.py`, `tests/eval/sets/`, `tests/probe_claude_development.py`, `tests/probe_claude_process_safety.py`, `tests/test_claude_gui.py`, `tests/test_claude_safe.py`

## Boundaries and invariants

- Edits only here, then `sync.py push`. Files in agent folders are not edited by hand.
- `sync.py push` does not overwrite a copy edited in place (`drift`); before overwriting it saves the previous text to `~/.local/share/solo-sdd/backup/`.
- Hooks are fail-open: an internal error lets the action through and is written to `~/.claude/hook-state/errors.log`.
- All repository text is in English, with no Cyrillic letter (`tests/test_repo_language.py`).

## Checks

Before "done": the `Tests` row, the lint from the table without output, `python3 -m solo_sdd validate --all`, `python3 sync.py status` without unexpected `drift`, the change's live scenario.

## Delivery

- Mode: pr
- Merge: squash
- PR title: the change name
- Deploy: no; deployment to agent folders is done separately (`sync.py push`).
- CI: an agent merges a PR through `sdd-pr.py merge` only when `sdd-pr.py wait <url>` gives `CI: green`. On `CI: red`, `CI: infra` or `CI: codeql` the agent fixes, reruns and waits again as `/ship` (under the dispatcher, `spec-dispatch`) says; a PR that is still not green waits for the owner: an agent never merges around a red or missing check (`docs/release.md`).

## Security

- Paid model calls in tests: only the cheapest (`global/model-policy.json`).
- `sync.py push` changes the agents' working folders on this computer: this is a prod action, check `sync.py status` after it.
- There are no secrets in the repository and there must be none.

## Lessons

- A stand runs exactly what it means to test: real inputs through the host, model runs as subagents of the agent's own session (never a separate `claude -p`), a base commit pinned by hash and read apart from the working folder, reads on a condition, every imported module copied. ([full text](LESSONS.md#stand-runs-what-it-tests))
- Environment detection looks only inside the passed home and PATH, a check of what another process will find runs in that process's own launch form, and a test fixture pins every git and interpreter default it relies on. ([full text](LESSONS.md#environment-facts))
- A claim about a tool's behaviour, a record of edited files or of affected tests, or a new test counted as run, is written only after checking it here against the tool on the realistic form of its input, the source or the suite runner's output. ([full text](LESSONS.md#probe-before-claim))
- An unnamed "our product" means solo-sdd itself; the owner's other products are neither the subject nor a source of facts unless named. ([full text](LESSONS.md#unnamed-product))
- A reader of a format, of a command's arguments or of another program's output reads it by that program's own rules and options, refuses broken or unknown input before its first side effect, and never drops an entry or a failed call silently. ([full text](LESSONS.md#formats-read-like-their-program))
- A session capability the agents depend on is probed once before launch; its absence stops the launch only when the project declares the need. ([full text](LESSONS.md#probe-capabilities))
- A check of printed output or a document matches by prefix and by whole item with whitespace collapsed, never by position or physical line. ([full text](LESSONS.md#output-checks-by-prefix))
- A stand that grades a judgement call expects one answer only where every correct reading gives it. ([full text](LESSONS.md#judgement-stands))
- A deployment gate is worded for the whole repository, a publication target handed to a new name is guarded in every clone, and a deploying command is never run to learn its options. ([full text](LESSONS.md#deployment-gates))
- A cleanup removes only what the current map, its own sources or its setup's record name (never what settings name now), keeps and names everything else, and takes a source as gone only when it is missing. ([full text](LESSONS.md#cleanup-scope))
- Every reader and gate takes a setting, its source and the copy it reads from one shared definition, falling back to the default only when the command or the tree is missing, never on an error or an empty answer. ([full text](LESSONS.md#setting-sources))
- A bulk wording replacement keeps quoted program output verbatim and is reread line by line. ([full text](LESSONS.md#bulk-wording))
- A script that moves or rewrites a branch decides from the commits themselves, never from a setting. ([full text](LESSONS.md#branch-scripts-from-commits))
- An input check and a limit on a foreign call each hold at one point every reader or caller passes and cover the edge forms of that input, and a read moved into a helper keeps every error its old caller caught. ([full text](LESSONS.md#input-edge-forms))
- Before a test of a removed requirement is deleted, its checks for kept requirements move into a kept test. ([full text](LESSONS.md#removed-requirement-tests))
- A new outcome, exemption or ban of a step is written where the rule it changes is read, and checked against every rule that requires what it bans. ([full text](LESSONS.md#new-outcomes-where-read))
- A scenario of a new behaviour names what only the new code produces, a scenario's test asserts the literal form its THEN names, and a plan for a feature covers its life around the request. ([full text](LESSONS.md#scenarios-only-new-code))
- A gate a person's marks open takes the confirmation from a record the agent cannot produce, and evidence the agent writes is matched against a source written before the work. ([full text](LESSONS.md#gates-from-sources))
- A guard that exempts part of a shell command reads it by the shell's and each program's grammar, refuses what it cannot read, and is replayed against the forms decided before. ([full text](LESSONS.md#shell-guards))
- A git-ignored path or a file a run creates is guarded through every git step that can delete it (merge, rebase, reset, abort, mirror) by git's own untracked list, and stays ignored or outside the tree even when the run fails. ([full text](LESSONS.md#ignored-paths))
