# work-hooks-subagents Specification

## Purpose
Claude Code workflow hooks in a session where the main agent hands work to background subagents: do not hinder the handout, give subagents the project context and check the status handback.

## Requirements

### Requirement: Stop waits for background agents
The `stop` subcommand SHALL skip all readiness checks if the Stop input has at least one `background_tasks` entry with `status: running`. If there are no such entries or the field is missing, the checks run as before.

#### Scenario: The dispatcher waits for orchestrators
- **WHEN** Stop comes with `background_tasks` where one task is `running`, and the session has an uncommitted edit
- **THEN** `stop` prints nothing and does not return the agent

#### Scenario: All background tasks finished
- **WHEN** Stop comes with `background_tasks` without `running` tasks, and there is an uncommitted edit
- **THEN** `stop` returns the agent with the previous reason about uncommitted edits

### Requirement: Subagent project context
The `subagent-context` subcommand on the SubagentStart event SHALL add the project context to the subagent (`additionalContext`) no longer than 4000 characters: the absolute path to the main project folder's `AGENTS.md` with an instruction to read it before work (if the file exists) and the list of open changes of the main project folder (the shared `.git`, where `CLAIM` lies) with `CLAIM` and `WAITING` marks (if it has `solo-sdd/changes`). The `AGENTS.md` path goes first and survives trimming.

#### Scenario: A subagent in a project with rules and changes
- **WHEN** a subagent starts with `cwd` in a project that has `AGENTS.md` and a change with `CLAIM`
- **THEN** the context holds the path to `AGENTS.md` and the line of this change with the `CLAIM` mark, the length is at most 4000 characters

#### Scenario: A subagent outside a project
- **WHEN** the subagent's `cwd` is not in a git repository
- **THEN** the output is empty

#### Scenario: The AGENTS.md text is not copied
- **WHEN** the project has `AGENTS.md`
- **THEN** the context holds the path to it, but not its full text

#### Scenario: Neither rules nor changes
- **WHEN** `cwd` is in a git repository without `AGENTS.md` and without open changes
- **THEN** the subcommand prints nothing

### Requirement: Status check on handback
The `guard` subcommand SHALL on PreToolUse of the `SubagentHandback` tool check the `message` field by the requirements of the capability `orchestrator-status` and on a mismatch refuse (`permissionDecision: deny`) with the list of mismatches. An internal check error lets the handback through and is written to `~/.claude/hook-state/errors.log`, like the other hook errors.

#### Scenario: A wrong status does not reach the dispatcher
- **WHEN** an orchestrator hands back `STATUS: archived` without a removed CLAIM
- **THEN** the handback is refused, the orchestrator gets the list of mismatches

#### Scenario: A git failure during the check
- **WHEN** the `WORKTREE` folder has `.git`, but the git command ends with an error or does not answer
- **THEN** the handback passes, an entry appears in `errors.log`

#### Scenario: WORKTREE is not a working copy
- **WHEN** there is no `WORKTREE` folder or it has no `.git`
- **THEN** it is a status mismatch: the handback is refused, the mismatch is named

### Requirement: Hook registration
`global/work_hooks_settings.py` SHALL connect `subagent-context` on SubagentStart and `guard` for the `SubagentHandback` tool, keeping a settings backup and creating no duplicates on a repeated run. If the settings `env` has no `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH`, the script SHALL write the value `"2"`; it does not change a value already set and prints it. The script SHALL keep the owner's rule in `autoMode.allow` by the requirement Owner merge rule in auto mode.

#### Scenario: A repeated connection
- **WHEN** `work_hooks_settings.py` runs twice
- **THEN** the settings have exactly one `subagent-context` entry on SubagentStart, and the `guard` matcher includes `SubagentHandback` once

#### Scenario: The depth is not set
- **WHEN** `~/.claude/settings.json` has no `env` or it has no `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH`
- **THEN** after the run `env` has `"CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH": "2"`, the other `env` variables are unchanged

#### Scenario: The depth is set by the owner
- **WHEN** `env` already has `"CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH": "3"`
- **THEN** the value stays `"3"`, the script prints that the depth is set by the owner

#### Scenario: The merge rule after a repeated run
- **WHEN** `autoMode.allow` holds the owner's previous rule about `gh pr merge`, and `work_hooks_settings.py` runs twice
- **THEN** `autoMode.allow` has one owner rule, it names `sdd-pr.py merge`, `sdd-pr.py land` and updating the change branch, and `gh pr merge` only for a repository without a `solo-sdd/` tree; the other `autoMode.allow` entries are unchanged and keep their order

### Requirement: Interface check by subagents
The `stop` check "the interface changed, and there was no browser check" SHALL count a check made by any subagent of this session: browser tools, skills from the interface check list and Bash commands with browser signs are also looked for in the subagent transcripts (the folder `<session id>/subagents/` next to the session transcript). A browser sign in Bash also includes a connection to the Chromium debug port (`--remote-debugging-port`, `json/version`, `webSocketDebuggerUrl`).

#### Scenario: The orchestrator made the check
- **WHEN** the main session merged an edit of `App.tsx`, and the orchestrator called the `ui-check` skill
- **THEN** `stop` does not require an interface check

#### Scenario: Nobody made the check
- **WHEN** the interface changed, and neither the session nor its subagents opened a browser
- **THEN** `stop` returns the agent with the previous reason

### Requirement: Owner merge rule in auto mode
`global/work_hooks_settings.py` and `install --hooks` SHALL keep one owner rule in `autoMode.allow`: merging an own checked PR with `sdd-pr.py merge` or `land`, updating the change branch from main (`git merge origin/<main>`), and `gh pr merge` from `/ship` in a repository without `solo-sdd/` are approved work, except under `delivery.merge-by: human` or when a merge or push triggers a prod deploy. The rule starts with the prefix `The owner's merge rule (solo-sdd)` and names no rules file.

#### Scenario: Replacement by the prefix
- **WHEN** on a repeated run `autoMode.allow` has an entry with the prefix `The owner's merge rule (solo-sdd)` or the old prefix `The owner's global rules (~/.claude/CLAUDE.md, section 13)` and other entries
- **THEN** that entry is replaced by the current rule text, the other entries stayed in place

#### Scenario: A bare API merge
- **WHEN** the agent runs `gh api -X PUT …/merge` without `sdd-pr.py`
- **THEN** the rule does not approve such a command directly

#### Scenario: A prod deploy
- **WHEN** a merge or push triggers a prod deploy
- **THEN** the rule does not call such a merge approved work

#### Scenario: A human merge project
- **WHEN** the rule text is read
- **THEN** it says a project with `delivery.merge-by: human` is merged by a person, names `gh pr merge` only for a repository without a `solo-sdd/` tree and does not name `~/.claude/CLAUDE.md`

### Requirement: Stop respects human merge
The `stop` hook SHALL NOT return the agent for an open unmerged PR when the project's `delivery.merge-by` is `human`; the other stop reasons SHALL stay.

#### Scenario: An open PR in human mode
- **WHEN** the session's PR is open and green, and `merge-by: human`
- **THEN** the stop hook lets the session end

### Requirement: Review before archive
`guard` SHALL refuse a Bash command that runs `solo-sdd archive <id>` when the actor's transcript (the session's, or for a subagent call its own `subagents/agent-<id>.jsonl`) has an edit (`Write`, `Edit`, `MultiEdit`, `NotebookEdit` or a Bash edit) of a file of the working copy outside `solo-sdd/` and `docs/`, and no `Agent` call whose description starts with `Review:` comes after the first such edit; the reason SHALL name that file. Otherwise the command SHALL pass.

#### Scenario: No review
- **WHEN** the session edited `src/app.py` and ran no `Review:` agent, then runs `solo-sdd archive add-words --yes`
- **THEN** the command is refused, the reason names `src/app.py`

#### Scenario: A review only before the code
- **WHEN** a `Review:` agent ran before the session's first edit of `src/app.py` and none after it
- **THEN** the archive is refused

#### Scenario: Fixes after the review
- **WHEN** a `Review:` agent ran after the first code edit, and the session then fixed `Nit` findings in `src/app.py`
- **THEN** the archive passes: the rounds of `spec-next` decide on re-review, not the guard

#### Scenario: Only artifacts after the review
- **WHEN** after the `Review:` agent the session edited only `solo-sdd/changes/add-words/tasks.md`
- **THEN** the archive passes

#### Scenario: A Bash edit
- **WHEN** the session wrote `src/app.py` only through a Bash heredoc and ran no `Review:` agent
- **THEN** the archive is refused, the reason names `src/app.py`

#### Scenario: An orchestrator subagent
- **WHEN** an orchestrator subagent edited `src/app.py`, launched a `Review:` agent after it and runs the archive, while the main session ran no review
- **THEN** the archive passes: the orchestrator's own transcript decides

#### Scenario: An unreadable transcript
- **WHEN** the transcript file is missing or cannot be read
- **THEN** the command passes and the error is written to the hook error log, as for every hook failure

### Requirement: Direct merge refused in a process tree
`guard` SHALL refuse a Bash command that runs `gh pr merge` or a `gh api` call to `pulls/<n>/merge` when the git working copy of the hook's `cwd` has a `solo-sdd/` tree, naming `sdd-pr.py merge`, whose gates a direct merge skips; outside such a tree it passes. A quoted argument, a heredoc body read by a text program and a search pattern are not commands. The check guards against an agent's accidental direct merge by the plain forms; it is not a security boundary.

#### Scenario: A process tree
- **WHEN** the project has `solo-sdd/` and the agent runs `gh pr merge 5 --squash`
- **THEN** the command is refused, the reason names `sdd-pr.py merge`

#### Scenario: The API form
- **WHEN** the project has `solo-sdd/` and the agent runs `gh api -X PUT repos/o/r/pulls/5/merge`
- **THEN** the command is refused

#### Scenario: No tree
- **WHEN** the repository has no `solo-sdd/` and the agent runs `gh pr merge 5 --squash`
- **THEN** the command passes

#### Scenario: Text about a merge
- **WHEN** the agent runs `git commit -m "explain gh pr merge"` in a project with `solo-sdd/`
- **THEN** the command passes: a message is not a command

### Requirement: Known bypasses of the merge guard
These direct merge forms SHALL pass `guard` as outside it, each pinned by a test that it passes: `xargs`, `find -exec`, `sudo -u`, `env -u`, a shell function, `bash -c`, `eval` or a quoted assignment after `A=(…)` or in `=(…)`, substitutions nested deeper than 3, a `)` in a pattern or quoted text that ends a substitution early, a quoted `(` that keeps one open, a backslash-newline between `$` and `(`. Branch protection is the boundary.

#### Scenario: A known bypass closed
- **WHEN** a change makes `guard` refuse one of these forms
- **THEN** the known-limit test fails until the form moves to the refused tests and `docs/hooks.md`

#### Scenario: A known false refusal
- **WHEN** a command with `$'`, `=(`, `${` or a `#` word has `(`, `;`, `|` or a newline before `gh pr merge` inside a message, as in `git commit -m "fix #42 (gh pr merge is refused)"` or `A=(x y); git commit -m "a; gh pr merge later"`
- **THEN** it is refused: in such a form quotes are ignored, and the test pins it

#### Scenario: An array assignment before a merge
- **WHEN** the agent runs `A=(1 2) gh pr merge 5`, `cat =(gh pr merge 5)`, `A=(1 2) \gh pr merge 5` or `cat =(/usr/bin/env gh pr merge 5)` in a project with a `solo-sdd/` tree
- **THEN** `guard` refuses it: a line with `=(` is read with quotes ignored, so the merge after it is found

#### Scenario: A quote inside a word after an array assignment
- **WHEN** the agent runs `A=(1 2) 'g'h pr merge 5` or `cat =(gh p''r merge 5)` in a project with a `solo-sdd/` tree
- **THEN** `guard` lets it through: a quote inside a word after `A=(…)` or in `=(…)` is a known bypass, pinned by a test that it passes

### Requirement: Archive run behind runners and options
`guard` SHALL recognise `solo-sdd archive <id>` (also `openspec`, `python -m solo_sdd`) for the CLAIM refusal and Review before archive: after a runner (`uv run`, `uvx`, `npx`, `pipx run`, `npm exec`), behind the values of options of the runner, of `sudo`, of `env` and of Python (`-W`, `-X`), with a joined `-msolo_sdd`, and in a `-c` string after `--`.

#### Scenario: A runner option value named like the program
- **WHEN** the session edited `src/app.py`, ran no `Review:` agent and runs `uvx --from solo-sdd solo-sdd archive add-words`
- **THEN** the command is refused, the reason names `src/app.py`

#### Scenario: A runner that starts Python
- **WHEN** the same session runs `uv run python -m solo_sdd archive add-words`
- **THEN** the command is refused

#### Scenario: Valued options
- **WHEN** the same session runs `python3 -W ignore -m solo_sdd archive add-words`, `python3 -msolo_sdd archive add-words`, `sudo -u root solo-sdd archive add-words` or `env -u X solo-sdd archive add-words`
- **THEN** each is refused

#### Scenario: End of options before the -c string
- **WHEN** the same session runs `bash -c -- 'solo-sdd archive add-words'`
- **THEN** the command is refused

#### Scenario: Words that stay text
- **WHEN** the same session runs `echo solo-sdd archive add-words` or `uvx --from solo-sdd solo-sdd validate --all`
- **THEN** the command passes

### Requirement: Checks without the policy
When `model-policy.json` cannot be read or parsed, `guard` SHALL still run every check that does not need it (secrets, worktrees, merges, the foreign CLAIM of the archive guard, CLAIM and WAITING), SHALL let through only the checks that read the policy (the model rules of test and Codex commands, the role and model rules of `Agent`, the review gate of the archive guard) and SHALL write the error to `errors.log`.

#### Scenario: A broken policy
- **WHEN** `model-policy.json` holds `{` and the agent runs `git worktree add ../wt`
- **THEN** the command is refused as with a valid policy, and `errors.log` has a line naming the policy

#### Scenario: Model checks let through
- **WHEN** `model-policy.json` holds `{` and the agent launches `Agent` "Review: x" with `model: haiku`
- **THEN** the call passes, and `errors.log` has a line naming the policy

### Requirement: Hook errors in the session context
The SessionStart `context` hook SHALL add one line `hook errors: <n> in the last 7 days, last: <line>` when `errors.log` has lines dated within the last 7 days, also when the context has nothing else; no line otherwise. A line without a leading ISO time is not counted.

#### Scenario: A recent error
- **WHEN** `errors.log` has two entries of yesterday
- **THEN** the context has `hook errors: 2 in the last 7 days` and the later entry

#### Scenario: Old errors only
- **WHEN** every entry is older than 7 days
- **THEN** the context has no hook errors line

#### Scenario: Errors outside a project
- **WHEN** the session starts in the home folder and `errors.log` has an entry of today
- **THEN** the hook emits a context with the hook errors line

### Requirement: Error log size
The SessionEnd hook SHALL keep the last 1000 lines of `errors.log` and drop older lines.

#### Scenario: A long log
- **WHEN** `errors.log` has 1500 lines at SessionEnd
- **THEN** it has the last 1000 of them afterwards

### Requirement: Browser signs from the policy file
The `stop` interface check SHALL count the built-in browser signs (the tool prefixes, interface-check skills and Bash signs the hook holds today) together with the string lists `tools`, `skills` and `bash` of the `browser` key of the deployed `model-policy.json`; a Bash sign is a plain substring, not a pattern. A user's list SHALL add signs and SHALL NOT remove a built-in one. The shipped `global/model-policy.json` SHALL hold the built-in values in that key.

#### Scenario: Another browser tool
- **WHEN** the deployed policy file adds the prefix `mcp__mybrowser__` to `browser.tools`, and a subagent called `mcp__mybrowser__open` after an interface edit
- **THEN** `stop` does not require an interface check

#### Scenario: A built-in sign removed from the copy
- **WHEN** the deployed copy's `browser.bash` no longer lists `--remote-debugging-port`, and the session ran a Bash command with it after an interface edit
- **THEN** `stop` does not require an interface check

#### Scenario: The shipped values
- **WHEN** a test reads `global/model-policy.json` and the hook's built-in signs
- **THEN** the `browser` key holds exactly the built-in prefixes, skills and Bash signs

### Requirement: Broken browser key fails open
A `browser` key or part that is missing adds nothing; one that is not an object or not a list of non-empty strings, and a policy file that cannot be read or parsed SHALL add nothing for that part and write one line naming it (`browser`, `browser.<part>` or the file) to `~/.claude/hook-state/errors.log`; the built-in signs and the rest of `stop` SHALL still apply.

#### Scenario: A broken key
- **WHEN** `browser` holds a number instead of an object
- **THEN** the hook counts the built-in signs and `errors.log` gets a line naming `browser`

#### Scenario: A policy file that does not parse
- **WHEN** the deployed `model-policy.json` is not valid JSON and the interface changed with no browser check
- **THEN** `stop` still returns the agent with the interface-check reason, and `errors.log` names the file

#### Scenario: An empty sign
- **WHEN** `browser.bash` holds `""`, which as a substring would match every command
- **THEN** that part adds nothing and `errors.log` names `browser.bash`

### Requirement: Policy file is the user's
The comment of `global/model-policy.json` and `docs/hooks.md` SHALL say that the model lists and the `browser` key are edited in the deployed copy `~/.claude/hooks/model-policy.json`, that `install`, `update` and `sync.py push` keep an edited copy as `drift` instead of overwriting it, so a newer shipped model list is not taken while it is `drift`, and how to take it, as probed.

#### Scenario: An edited copy
- **WHEN** a user added a model to `cheap` in the deployed copy and runs `python3 sync.py push`
- **THEN** the copy stays as edited and `sync.py status` shows it as `drift`
