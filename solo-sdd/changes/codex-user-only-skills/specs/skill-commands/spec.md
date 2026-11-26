## ADDED Requirements

### Requirement: User-only skills in Codex
Every `skills/*/SKILL.md` whose frontmatter holds `disable-model-invocation: true` SHALL have `agents/openai.yaml` in its folder with `policy.allow_implicit_invocation: false`, laid out by `targets.json` next to that skill's `SKILL.md` for every agent the skill goes to, so Codex does not pick it by its description; a skill without that frontmatter line SHALL have no such policy. A test SHALL name each skill that breaks the pairing.

#### Scenario: A new user-only skill without the file
- **WHEN** a skill gets `disable-model-invocation: true` and its folder has no `agents/openai.yaml`
- **THEN** the pairing test fails naming the skill

#### Scenario: A model-invoked skill with the policy
- **WHEN** `skills/spec-next/agents/openai.yaml` holds `allow_implicit_invocation: false` and `skills/spec-next/SKILL.md` has no `disable-model-invocation` line
- **THEN** the pairing test fails naming `spec-next`

#### Scenario: A user-only skill with the wrong policy
- **WHEN** `skills/report/agents/openai.yaml` holds `allow_implicit_invocation: true`, or no `policy` key
- **THEN** the pairing test fails naming `report`

#### Scenario: A file not laid out
- **WHEN** `skills/report/agents/openai.yaml` exists and `targets.json` has no entry that lays it out
- **THEN** the pairing test fails naming `report`

#### Scenario: The layout
- **WHEN** `sync.py push` runs into a temporary `HOME` that holds an empty `~/.codex` folder, so Codex is detected
- **THEN** `~/.codex/skills/report/agents/openai.yaml` and `~/.agents/skills/report/agents/openai.yaml` exist and hold `allow_implicit_invocation: false` as a YAML boolean, and neither skills folder has `spec-next/agents/`
