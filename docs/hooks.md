# Claude Code hooks

## Claude Code workflow hooks

The hooks close the most frequent repeats in work with an agent: reading the project rules, continuing, archiving, merging, status. One script `global/work_hooks.py`, subcommands:

| Subcommand | Event | What it does |
|---|---|---|
| `context` | SessionStart | Puts into the context AGENTS.md (unless CLAUDE.md imports it with `@AGENTS.md`), `solo-sdd/project.md` (`openspec/config.yaml` in a project still on `openspec/`), `docs/status.md`, the branch, `git status`, changes with progress and CLAIM/WAITING markers; a `hook errors: <n> in the last 7 days, last: <line>` line when `errors.log` has entries of the last 7 days, also outside a project; an `integration errors:` line, see [Integrations](integrations.md) |
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
