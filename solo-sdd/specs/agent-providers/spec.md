# agent-providers Specification

## Purpose
Describes the agents solo-sdd supports, how it detects them, what it deploys for each and which protections each one lacks, so a user with any agent gets exactly what works there.

## Requirements

### Requirement: Provider registry
The package SHALL hold one entry per supported agent with its name, detection, skill root, global and project rules files, and capabilities (`hooks`, `subagents`), each capability with the agent version it was checked on or `unverified`; `hooks` counts as present only where a no-op hook ran in the probe. `claude`, `codex`, `cursor` and `other` SHALL be registered.

#### Scenario: Registry listing
- **WHEN** `solo-sdd doctor` runs
- **THEN** the providers `claude`, `codex`, `cursor`, `other` are known, each with its capabilities

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

### Requirement: Capability gaps named
`solo-sdd doctor` SHALL print one line per chosen agent: `ok agent <name>: <capabilities>` when it has hooks and subagents, otherwise `warn agent <name>: no <capability>: <what is not enforced>`; for an agent whose skill root no probe has recorded, the gaps SHALL follow `unverified: skills, project rules: <where they come from>`. A skill that needs capabilities (`spec-dispatch`: subagents and hooks) SHALL be deployed only to providers that have them.

#### Scenario: Codex without hooks
- **WHEN** `codex` is chosen and its hooks capability is not confirmed
- **THEN** `warn agent codex: no hooks:` followed by the CLAIM guard, the secret guard and the stop check

#### Scenario: spec-dispatch placement
- **WHEN** `install --agents claude,codex` runs
- **THEN** `spec-dispatch` is in `~/.claude/skills` only

### Requirement: Agents setting
The settings key `agents` SHALL hold the project's agents as a list of registered names, default the detected ones; an unregistered name SHALL be refused by `solo-sdd config set`.

#### Scenario: Set agents
- **WHEN** `solo-sdd config set agents claude,copilot` runs and `copilot` is not registered
- **THEN** exit 1 with the registered names

#### Scenario: Project agents not installed
- **WHEN** `solo-sdd/config` of the current project sets `agents: codex` and the installed choice lacks `codex`
- **THEN** `solo-sdd doctor` prints `warn project-agents:` naming `codex` and the `solo-sdd install --agents` command

### Requirement: Cursor provider
The registry SHALL have a `cursor` provider detected by the `cursor-agent` command or its folder `~/.cursor`. Its skill root, rules file and capabilities SHALL come from a probe of an installed Cursor version; until then each SHALL be `unverified`, `install --agents cursor` SHALL deploy only the `other` provider's files, and `doctor` SHALL name the unverified capabilities.

#### Scenario: Not probed
- **WHEN** `cursor` is chosen and no probe result is recorded
- **THEN** `doctor` prints `warn agent cursor: unverified: skills, project rules:` followed by the `no hooks:` and `no subagents:` gaps

#### Scenario: Install not probed
- **WHEN** `install --agents cursor` runs on a clean home and no probe result is recorded
- **THEN** only the `other` and shared copies are written, nothing under `~/.cursor`, and the output says that project rules come from `solo-sdd init`

#### Scenario: Detected by its folder
- **WHEN** `cursor-agent` is not in PATH and the home has `~/.cursor`
- **THEN** `cursor` is among the detected agents

#### Scenario: Probed
- **WHEN** the probe found that the installed Cursor reads `AGENTS.md` and loads skills from a folder, and the registry records that folder and the confirmed capabilities with the Cursor version
- **THEN** `install --agents cursor` deploys the skills there and the `doctor` line of `cursor` has no `unverified:` part

### Requirement: Probe without side effects
The Cursor probe SHALL install nothing, SHALL run only against a temporary project and home, and SHALL print one line per capability with `confirmed`, `absent` or `not run` and the Cursor version.

#### Scenario: No Cursor
- **WHEN** the probe runs on a machine without Cursor
- **THEN** every line says `not run`, exit code 0, no file outside the temporary folders changes

### Requirement: Vendor files per skill
A `targets.json["files"]` entry for a file laid out into skill folders SHALL name each skill once with the path inside it, and no agent folder. The layout SHALL put the file into that skill's folder of every agent the skill's `SKILL.md` is laid out for, and of no other agent. An entry naming a skill absent from `targets.json["skills"]` SHALL stop `install`, `push` and `status` with code 1 naming the entry, writing nothing.

#### Scenario: The same layout
- **WHEN** `python3 sync.py status` runs before and after the change on the same home
- **THEN** both list the same target paths with the same states

#### Scenario: One agent chosen
- **WHEN** `install --agents claude` runs
- **THEN** `antislop.md` is laid out into the `ui-check` and `copy-check` skill folders of Claude only

#### Scenario: An agent without a skill folder
- **WHEN** `install --agents cursor` runs
- **THEN** no vendor file is laid out under `~/.cursor/`, and the `other` folder `~/.agents/skills/ui-check/antislop/` gets them

#### Scenario: An unknown skill
- **WHEN** an entry names the skill `no-such-skill` and `python3 sync.py status` runs
- **THEN** code 1, the output names the entry and `no-such-skill`, no file in the home changed

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
