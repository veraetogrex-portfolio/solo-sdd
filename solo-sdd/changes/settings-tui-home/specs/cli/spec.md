## ADDED Requirements

### Requirement: Uninstall hooks only
`solo-sdd uninstall --hooks` SHALL remove from `~/.claude/settings.json` only what `_hooks` records, with a settings backup, keep every copy, the rules block and every entry a person added, and clear `_hooks`. With nothing recorded it SHALL write no file and say the hooks are not connected.

#### Scenario: Connected hooks
- **WHEN** `install --hooks` ran, then `uninstall --hooks` runs
- **THEN** the hook entries, `statusLine`, the `autoMode` rule and the depth variable it added are gone, `solo-sdd status` shows every copy as before, `_hooks` is empty

#### Scenario: A person's hook kept
- **WHEN** `settings.json` also has a hook a person added
- **THEN** after `uninstall --hooks` that hook is still there

#### Scenario: Broken settings
- **WHEN** `_hooks` records connected hooks and `settings.json` does not parse as JSON
- **THEN** `fail settings: <reason>` is printed, no file changes, `_hooks` is kept, exit code 1

#### Scenario: Nothing connected
- **WHEN** `_hooks` is empty
- **THEN** no file is written and the output says the hooks are not connected
