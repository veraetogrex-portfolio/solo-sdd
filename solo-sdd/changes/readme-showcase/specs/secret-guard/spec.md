## MODIFIED Requirements

### Requirement: Known bypasses of the Bash guard
`docs/hooks.md` SHALL name as outside the Bash guard: brace expansion, `sh -c` with the file as a positional argument, process substitution with a quoted `)`, a heredoc marker line with an open quote, `${X:-env}` and BSD `sed r` without a space; the boundary SHALL be `Read(**/.env)` in `permissions.deny` and secrets kept only in `.env`.

#### Scenario: A known bypass
- **WHEN** the agent runs `cat .e{n,}v` or `sh -c 'cat "$1"' _ .env`
- **THEN** the guard lets it through and `docs/hooks.md` lists the form as a known bypass
