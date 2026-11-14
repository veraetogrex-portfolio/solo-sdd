## MODIFIED Requirements

### Requirement: Process guard connected
`solo-sdd install --hooks` SHALL connect `process-guard.py` as a PreToolUse hook on `Bash|Monitor` as `docs/hooks.md` names it, with deny rules for `pkill`, `killall`, `kill`, `osascript`, `launchctl`, `shutdown`, recording in `_hooks` only what it added and never duplicating an entry connected by hand. `uninstall` SHALL remove only the recorded entries. `doctor` SHALL print `ok process guard: connected` or `warn process guard: not connected`.

#### Scenario: Connected by hand
- **WHEN** `settings.json` already has the process-guard hook entry and `install --hooks` runs
- **THEN** there is one such entry, `_hooks` does not record it, `uninstall` keeps it

#### Scenario: A fresh home
- **WHEN** `install --hooks` runs on a home without settings and then `uninstall`
- **THEN** after install the hook and the six deny rules are there, after uninstall none of them
