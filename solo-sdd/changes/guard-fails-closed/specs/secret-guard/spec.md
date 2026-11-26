## ADDED Requirements

### Requirement: Secret checks fail closed
When `guard_env_write`, `guard_env_read` or `guard_secrets_bash` raises, or the preparation of its input in `cmd_guard` raises (a path or command text built for it), `guard` SHALL answer `deny` with a reason naming the check and `~/.claude/hook-state/errors.log`, and SHALL write the error there as before. An exception in any other check SHALL keep letting the call through.

#### Scenario: A raising Bash secret check
- **WHEN** `guard_secrets_bash` raises while the agent runs `cat .env.local`
- **THEN** the answer is `deny`, its reason names `guard_secrets_bash` and `errors.log`, and `errors.log` holds the error

#### Scenario: A raising read check
- **WHEN** `guard_env_read` raises on a `Read` of `README.md`
- **THEN** the answer is `deny` naming `guard_env_read`

#### Scenario: A raising Write check
- **WHEN** `guard_env_write` raises on a `Write` of `notes.md`
- **THEN** the answer is `deny` naming `guard_env_write`

#### Scenario: Preparation raises
- **WHEN** `command_text` raises while `guard` prepares a Bash command for `guard_secrets_bash`
- **THEN** the answer is `deny` naming `guard_secrets_bash`

#### Scenario: Another check raises
- **WHEN** `guard_models_agent` raises on an `Agent` call
- **THEN** the call passes and `errors.log` holds the error

### Requirement: Unreadable guard input refused
`guard` SHALL answer `deny` naming `guard input` and `~/.claude/hook-state/errors.log`, and write the error there, when stdin is not a JSON object, or a call of Bash, Read, Grep, Write, Edit, MultiEdit or NotebookEdit has a `tool_input` that is not an object or a `cwd` that is not a string. A present `command`, `file_path` or `notebook_path` that is not a string SHALL deny naming its secret check instead. Other tools pass as before.

#### Scenario: Stdin is not a JSON object
- **WHEN** `guard` gets `[1]`, an empty stdin or text that is not JSON
- **THEN** the answer is `deny` naming `guard input`, and `errors.log` holds the error

#### Scenario: A field of the wrong type
- **WHEN** `guard` gets a `Read` with `cwd` `5`, `0` or `[]`, a Read, Bash or Write call whose `tool_input` is `["README.md"]`, `0` or `[]`, a Bash call with `command` `5`, `0`, `[]` or `false`, a `Write` with `file_path` `5` or `0`, a `Read` with `file_path` `5` or `["a/.env"]`, or a `NotebookEdit` with `notebook_path` `["a.ipynb"]`
- **THEN** the answer is `deny` naming `guard input` for the `cwd` and `tool_input` cases, `guard_secrets_bash` for `command` and `guard_env_write` for the Write `file_path` and `notebook_path`, and `guard_env_read` for the Read `file_path`

#### Scenario: Absent fields and other tools
- **WHEN** `guard` gets a `Read` with `cwd` null, a Bash call with `command` null, a `Write` with `tool_input` null, or an `AskUserQuestion` with `tool_input` `0` and `cwd` `5`
- **THEN** no answer comes

#### Scenario: Hostile command text
- **WHEN** `guard` gets a Bash command with unbalanced quotes, an unterminated heredoc, nested `$(` and backquotes (1,000 levels of `$(` at most), or 100,000 characters of `\"` pairs or of `a |` inside one quoted `grep` pattern, none naming a secret
- **THEN** no answer comes, `errors.log` stays empty, and each call returns within 5 seconds
