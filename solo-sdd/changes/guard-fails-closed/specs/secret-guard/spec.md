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
