## MODIFIED Requirements

### Requirement: Install for chosen agents
`solo-sdd install --agents a,b` SHALL deploy skills and files only for the named providers plus `other`; without the flag, for the stored choice, else the detected ones plus `other`. The choice SHALL be stored in the state and used by `status`, `update` and `uninstall`. A provider dropped from the choice SHALL lose its unchanged copies. An unknown name SHALL be refused before any file is written.

#### Scenario: Only Codex
- **WHEN** `solo-sdd install --agents codex` runs on a clean home
- **THEN** `~/.codex/skills` and `~/.agents/skills` get the skills, `~/.claude/skills` gets nothing

#### Scenario: A state from an earlier version
- **WHEN** the state has no agent choice
- **THEN** `install`, `status` and `update` treat it as `claude`, `codex`, `other`

#### Scenario: Unknown agent
- **WHEN** `install --agents copilt` runs
- **THEN** exit 1, the known names are listed, no file changes

#### Scenario: Repeated install keeps the choice
- **WHEN** `install --agents codex` ran before and `install` runs without the flag while `claude` is detected
- **THEN** the choice stays `codex`, `other` and `~/.claude/skills` gets nothing

#### Scenario: Narrowed choice
- **WHEN** `install --agents claude,codex` ran and then `install --agents codex` runs
- **THEN** the unchanged copies under `~/.claude` are removed, a copy edited in place is kept and named

#### Scenario: Hooks without Claude
- **WHEN** the Codex `hooks` capability is `unverified`, and `install --agents codex --hooks` runs, or `install --agents codex` while the hooks are connected
- **THEN** exit 1 naming that hooks need `claude` or a confirmed `codex`, no file changes

## ADDED Requirements

### Requirement: Codex hook probe
`tests/stands/provider-probe.py codex` SHALL run a no-op hook in a temporary `CODEX_HOME`, trusted the way the probed Codex version records trusted hooks, and record that version as the Codex `hooks` capability only when the hook ran; otherwise the capability SHALL stay `unverified` and the probe SHALL print the reason.

#### Scenario: The hook ran
- **WHEN** the no-op hook of the probe writes its marker file during the Codex run
- **THEN** the probe prints the Codex version for `hooks`, and the registry entry is updated with it

#### Scenario: The hook did not run
- **WHEN** the Codex run ends and the marker file is missing
- **THEN** the probe prints `hooks: unverified` with the reason, and the registry keeps `unverified`

### Requirement: Codex hook layout
With the Codex `hooks` capability confirmed, `solo-sdd install --hooks` for a choice with `codex` SHALL lay out `global/work_hooks.py` and `global/model-policy.json` into `~/.codex/hooks/` and write the `guard`, `context`, `stop` and `end` entries into `~/.codex/hooks.json` once, keeping every foreign entry and backing the file up before a rewrite. A differing file already there SHALL be a foreign copy (requirement Foreign copy kept).

#### Scenario: A clean Codex home
- **WHEN** `install --agents claude,codex --hooks` runs on a home with `~/.codex` and no `~/.codex/hooks.json`
- **THEN** `~/.codex/hooks/work_hooks.py` equals `global/work_hooks.py`, `hooks.json` has one entry per event, and a second run changes no file

#### Scenario: The hand copy
- **WHEN** `~/.codex/hooks/work_hooks.py` holds an older text with no state entry
- **THEN** `install` prints `foreign` for it, keeps it byte for byte and exits 1; with `--replace-foreign` it is replaced and its old text is in a backup folder

#### Scenario: A foreign entry kept
- **WHEN** `~/.codex/hooks.json` holds a `PreToolUse` entry of another tool
- **THEN** after `install` that entry is unchanged and the solo-sdd entries are added beside it

#### Scenario: A broken hooks file
- **WHEN** `~/.codex/hooks.json` is not valid JSON
- **THEN** `install --hooks` exits 1 naming the file, and no file under `~/.codex` is written

#### Scenario: Codex dropped from the choice
- **WHEN** `install --agents claude,codex --hooks` ran and then `install --agents claude --hooks` runs
- **THEN** the solo-sdd entries leave `~/.codex/hooks.json`, its foreign entries stay, and the unchanged hook copies under `~/.codex/hooks/` are removed

#### Scenario: A translation in Codex
- **WHEN** the laid-out hook gets a Codex `Stop` input whose transcript ends with the Russian request "translate into English", the reply is in English and the reply language is `ru`
- **THEN** the hook does not block the stop
