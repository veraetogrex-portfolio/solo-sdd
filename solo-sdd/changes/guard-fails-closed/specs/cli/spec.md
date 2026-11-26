## ADDED Requirements

### Requirement: Guard entry fails closed
`solo-sdd install --hooks` SHALL connect the `guard` PreToolUse entry of `work_hooks.py` with `onFailure: "block"` and its 10-second timeout, so a crash before the checks run or a timeout refuses the tool call, whichever check was slow. A missing `work_hooks.py`, or a `/usr/bin/python3` that does not run, SHALL still pass. The other `work_hooks.py` entries SHALL keep no `onFailure`. A settings file with the earlier `guard` entry SHALL get the new one on the next run.

#### Scenario: A fresh home
- **WHEN** `install --hooks` runs on a home without settings
- **THEN** the PreToolUse entry whose command ends in `work_hooks.py" guard` has `"onFailure": "block"` and `"timeout": 10`, and no entry of `context`, `subagent-context`, `beat`, `claims`, `stop` or `end` has `onFailure`

#### Scenario: An earlier install
- **WHEN** `settings.json` holds the `guard` entry without `onFailure` from an earlier `install --hooks` and `install --hooks` runs again
- **THEN** the file holds the `guard` entry once, with `"onFailure": "block"`, a backup is written and `uninstall` then removes it

#### Scenario: A guard that cannot start
- **WHEN** the `guard` command of the settings entry runs through `sh -c` with a `work_hooks.py` that has a syntax error
- **THEN** it exits with a code other than 0 and 2, the case Claude Code refuses under `onFailure: "block"`

#### Scenario: No script or no interpreter
- **WHEN** the same command runs with no `~/.claude/hooks/work_hooks.py`, with a `G` whose interpreter path does not exist, or with an interpreter that exits 1 at once (the macOS stub without Command Line Tools)
- **THEN** it exits 0 with no output
