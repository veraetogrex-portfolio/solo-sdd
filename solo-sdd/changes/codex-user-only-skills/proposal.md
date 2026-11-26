# Proposal

## Why

Seven skills are reachable only by the owner's command: `blockers`, `changes`, `health`, `next-up`, `relay`, `report` and `review-principles` carry `disable-model-invocation: true` in their frontmatter. That line is a Claude Code field. `targets.json` lays the same seven skills out for Codex too (`~/.codex/skills`) and for `other` (`~/.agents/skills`), and nothing in the repository tells Codex to keep them manual: `sync.py`, `solo_sdd/` and `tests/` hold no `agents/openai.yaml` and no `allow_implicit_invocation`. Codex picks a skill by its description when the task matches it, so a Codex session can start `/report` or `/next-up` on its own from a phrase like "what is next".

The Codex documentation names the switch: in a skill's `agents/openai.yaml`, `policy.allow_implicit_invocation: false` stops Codex from selecting the skill on its own, while `$skill` still calls it explicitly; the default is `true` (https://learn.chatgpt.com/docs/build-skills, read 2026-11-26). The skills repository of Matt Pocock (https://github.com/mattpocock/skills, `.agents/invocation.md`) keeps the two fields in step for every user-invoked skill.

## What Changes

- Each of the seven skills gets `skills/<name>/agents/openai.yaml` with `policy.allow_implicit_invocation: false`, laid out by `targets.json` next to the skill's `SKILL.md` for every agent that skill goes to.
- A test pairs the two fields both ways: a skill with `disable-model-invocation: true` and no such file, or a file with the policy `false` for a skill without the frontmatter line, fails naming the skill.
- `docs/layout.md` names the file and why it is there.

## Capabilities

### New Capabilities

### Modified Capabilities
- `skill-commands`: ADDED requirement User-only skills in Codex.

## Impact

- `skills/blockers/agents/openai.yaml`
- `skills/changes/agents/openai.yaml`
- `skills/health/agents/openai.yaml`
- `skills/next-up/agents/openai.yaml`
- `skills/relay/agents/openai.yaml`
- `skills/report/agents/openai.yaml`
- `skills/review-principles/agents/openai.yaml`
- `targets.json`
- `tests/test_skill_commands.py`
- `docs/layout.md`

## Out of Scope

- The `interface` block of `agents/openai.yaml` (display name, icons): Codex reads the skill name and description without it.
- Where Codex reads user skills: the current documentation names `$HOME/.agents/skills` and not `~/.codex/skills`, the folder `solo_sdd/providers.py` lays Codex skills into; whether that folder is still read, and whether a skill laid into both is listed twice, is a separate question.
- Codex hooks and the `onFailure` field.
- Neighbouring changes of this plan: `guard-fails-closed`, `history-guard`, `lesson-gate`.

## Depends On

none

## Source

The owner, 2026-11-26, on the comparison of solo-sdd with mattpocock/skills, skyremote/chief-of-staff-kit and davidondrej/skills (translated from Russian): "well, since you singled them out, make the changes". Item 1 of that comparison (translated): "Codex does not see the user-only mark: seven skills carry `disable-model-invocation: true`, a Claude Code field; `targets.json` lays them out for Codex as well, and the repository has no Codex counterpart."
