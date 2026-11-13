# solo-sdd

## Purpose and mode

Own spec-driven development process for one person or a team, with any coding agent, independent of other spec tools: the algorithm, skills, global agent rules, Claude Code hooks and project templates. The repository is the source of truth; `sync.py push` puts the files in place.
Mode: prod. Prod here is the agent folders on this computer (`~/.claude`, `~/.codex`, `~/.agents`, `~/.local/bin`): after `sync.py push` an edit takes effect in all sessions at once.

## Sources of truth

- Behaviour contract: `solo-sdd/specs/`; active work: `solo-sdd/changes/`; the project intent: `solo-sdd/project.md`.
- Algorithm: `ALGORITHM.md`; the lessons the rules grew from: `LESSONS.md`.
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
- No CI: while GitHub Actions starts no jobs (the spending limit, since 2026-11-08), `sdd-pr.py wait <url>` prints `PR #<n> <url> CI: infra` with no log line and exits with code 4 (probed on PR #79 on 2026-11-12). Then the full local run before delivery, `python3 tests/run.py --tier slow`, is the only suite check, and the PR waits for the owner: an agent never merges around a red or missing check (`docs/release.md`).

## Security

- Paid model calls in tests: only the cheapest (`global/model-policy.json`).
- `sync.py push` changes the agents' working folders on this computer: this is a prod action, check `sync.py status` after it.
- There are no secrets in the repository and there must be none.

## Lessons

- A stand runs what it means to test: a container stand gets the repository files and its downloads through stdin from the host (a container here has no network of its own and a bind mount sees only folders under the home folder), and a stand that runs a Python package with `-m` against a copy of the repository runs from outside the copy, since the working folder comes first on the import path; a stand that compares with the tree before its change pins that commit by hash, since the fork point from main and a lookup by the change's own commits move once the branch merges; a test that runs a copy of a project file copies every project module that file imports, so a new import does not break the copy.
- Detection of an installed agent or any other environment fact looks only inside the passed home and PATH, never at a machine-wide folder, and a test of such code pins what is detected, so it gives the same result on every machine; a setting proposed from detected facts requires every fact the command that uses it depends on, not only the one that makes it possible.
- A claim about how a tool behaves or what it outputs, taken from its changelog, its binary or another agent's report, is written into a skill, document, change or a command's own output only after running that tool here on a probe (with no run possible it is worded as expected and unconfirmed, never as a state), and a record of which files a change edited, or of which tests a source path affects, only after checking it against its source before the commit: the diff for the first, and for the second every way a test reaches the path (an import, a script another script starts, a copy it compares, a build run in the tree); text with escapes of non-ASCII characters is read back in the written file before the commit, since the writing tool may decode the escapes; a timing or cost measured on another machine or load is measured again here, base and branch under the same load, before a pass bar or a plan rests on it.
- An unnamed "our product" in a request means solo-sdd itself: the owner's other products are neither the subject of the work nor a source of its facts unless the owner names them.
- Markup that hides text (HTML comments) is removed once, in the reader, after code blocks and code spans are recognised, and no later consumer applies it again; a command that reads a format another program reads (a document `validate` checks, a shell command line) reads it with that program's own rules or a copy of its reader, never a regex of allowed prefixes, and accepts exactly what it accepts or refuses it, and a command that copies a tree and then advises deleting the source refuses on any entry it cannot list, follow or decode, and a gate or report over a document counts every line outside the part it exempts and keeps the readable entries of a file it cannot fully parse: a line or entry skipped silently is lost; a command that refuses a broken input checks it before its first side effect, also in the steps that run before its main one, and one that writes several files checks every target it can (readable, writable) before the first write, whichever order it writes in; in a fail-open handler an exception ends every later step, so a step that must always run comes before the steps that can raise, and each check loads a shared input (a policy file) through its own guarded read, so a broken input drops only the checks that need it.
- A session capability the agents depend on (loopback sockets, network, subagent depth) is probed once before they are launched; its absence stops the launch with the fix named only when the project declares that it needs the capability, otherwise the launch goes on with the fix as a warning.
- A check of a command's printed output finds a line by its prefix, not by its position, a check of a document reads a step or item whole up to the next one, not one physical line, and both collapse whitespace in both sides before comparing with a stated text: a new output line or a reflowed paragraph must not break old checks, and tools align output with runs of spaces.
- A stand that grades a judgement call expects one answer only for an input where every correct reading gives it; otherwise it grades what all correct answers share.
- A deployment gate is worded for the whole repository, not for one change: a push after any later merge deploys the whole tree, and a deployment the process starts for itself never takes a source that holds merged work not yet cleared for deployment; a publication step that hands a name others resolve to a new target (a repository renamed and its old name taken by a new one) first guards and repoints every clone that uses the name, and checks a push it forbids with a dry run, never with the push itself.
- A cleanup of copies an earlier version or a gone source deployed skips every path the current deployment map still lays out, names its candidates instead of matching all unmapped state entries, and takes a source as gone only when it is missing, never when it cannot be read for lack of permission (a folder that can be listed but not entered included); a removal in a folder the owner also writes to deletes only the entries its own sources name (the map, the state, its caches), keeps and names every other entry, and silences only the one error it expects (a folder not empty).
- A value that falls back to a built-in default is reported with its source, so a reader can tell "nothing set" from a choice, and a reader that switches on a listing tells a refusal (a FAIL line, a non-zero exit) from an empty answer, so a broken input never reads as the thing being off; every reader of a setting, the command a person runs included, takes its chain of sources from one shared definition, never from a fallback only one reader knows; and a choice inferred from older records is stored explicitly once made, so records a later step keeps never infer it back; a rule that says which of several values (two command rows, two settings) its readers take is written at every reader that a change finds by searching for the value's name, not only where the values are defined; a gate that asks for a command's run selects what it asks about with that command's own selection (the same function, both sides normalized the same way), so every request it makes is one a run can clear.
- A bulk wording replacement in instructions keeps quoted program output verbatim and is reread line by line for a shift of meaning.
- A script that moves or rewrites a branch decides from the commits themselves, never from a setting that other readers resolve from more sources than it does.
- An input check covers the edge forms of its input: a whole-number or name check accepts only ASCII digits and the whole string (`str.isdigit` passes digits that `int()` rejects, a regex `\d` with `$` passes other scripts' digits and a trailing newline), a check whether input comes from a terminal treats a closed stdin (no stream at all) as no terminal, and a comparison that decides whether to rewrite a stored value normalizes both sides the same way, line endings included; a write made atomic through a new file and a rename keeps every refusal of the write it replaces, checking the target's own write permission, since a rename needs only the folder's; text a reader takes from foreign input (a folder name, a line of a file) reaches its output only escaped, and a reader of a foreign tree refuses a link leading out of it before it prints anything read through the link; a stored result read back is checked against what the step that wrote it can produce, and printed exactly as stored, never cleaned a second way; a foreign command's process group is killed only while a process the caller has not yet reaped holds the group id; every reader of a file in a folder foreign input can reach opens it without blocking and parses only a regular file, and a result stored beside others in one record carries its own time, since the record's write dates every result it keeps; a check that tells a missing path from an unreadable one stats the path and catches only the not-found errors, never a library predicate (`Path.is_file`, `exists`) whose error handling changes between Python versions.
- Before a stand or test of a removed requirement is deleted, every check it holds for a requirement that stays moves into a kept test.
- A new outcome or exemption of a step is written where the rule it changes is read: before that step in the order, and as its exit in every state list the process keeps where that list's exit rule is written; otherwise the run takes the old path or waits for an event that never comes; a new ban is checked against every rule that requires what it bans, and names that rule's case as its exception.
- A scenario of a change that adds a behaviour names what only the new code produces, and an example project's own checks are ones its shipped open change already meets: otherwise a test written first passes on the old code, or the agent rewrites the example before code.
- A gate that a person's marks open counts the expected items from its own source and takes the person's confirmation from a record the agent's account cannot produce (a review the platform refuses the author), never from the marks alone or from parsing the agent's commands; evidence the agent writes itself (a LIVE command, a review field) is matched whole against a source written before the work, and the bypass flag of such a gate is the owner's alone.
- A guard that exempts part of a shell command (a message, a pattern, a path) reads it by the shell's grammar and each program's option grammar (clustered and abbreviated options, `$'…'`, a `#` comment, a `cd`, a wrapper that runs a word) and refuses every form it cannot read the same way: an exemption is kept as narrow as the forms it is proven on, and the fallback that drops it names the forms the reader can read (an allowlist), not every occurrence of a feared token; a check whether a pattern (a glob) reaches a protected name tests it against that name's own rule and the files that exist, never against a sample list of names; a reader of a nested part (a substitution, a `-c` string) takes it from the original text, never from a copy another reader rewrote (requoted, cut), and applies the same exemptions as at the top level; a guard that recognises a run behind wrappers and runners tries every later word instead of stopping at the first word it does not know, since that word may wrap the run: a false refusal is recorded as a known limit, a missed run is not; a form one rule learns to read stays unreadable for every other rule that refuses it for its own reason (a `${` computes a file name for the secret guard), so a scenario that expects a guard to pass is checked against every requirement of that guard on the same form; a fix that narrows or widens such a match is replayed against the forms the previous version decided, so no refused form starts passing and no command of another program starts being refused.
- A path that becomes git-ignored is checked through every step that merges, resets, aborts or mirrors the tree for a deletion of its copy on disk: git treats an ignored file as expendable and overwrites or removes it, a transfer of ignored files carries their removal, and an undo that runs after a reset deletes files git tracks again.
