## 1. Implementation

- [ ] 1.1 Rows in `tests/test_settings.py` named after Subagent model settings: the six keys with type, default and group `agents`, a model name with a space refused naming the allowed characters; the value strategies of the Config command property gain the six keys, model names with `.`, `-`, `[` and `]` among them; they fail first; then the keys and the model name kind in the settings block of `solo_sdd/settings.py` with `ABOUT` lines, `python3 scripts/sync_blocks.py --check` empty; the rows pass
- [ ] 1.2 Rows in `tests/test_work_hooks.py` named after Project models within the machine policy: a `sonnet` lookup and a `sonnet` orchestrator denied with the key and the list named, a `fable` reviewer allowed, no key keeps the role rules, the bypass variable lifts the refusal, a broken config keeps the role rules and writes `errors.log`; they fail first
- [ ] 1.3 `global/work_hooks.py` reads the role keys from the event folder's `solo-sdd/config` and checks a launch on the set model against the role list; the rows of 1.2 pass and the existing guard tests keep every assertion
- [ ] 1.4 `skills/spec-dispatch/SKILL.md`, `skills/spec-next/SKILL.md`, `skills/spec-next/acceptance.md`, `skills/spec-audit/SKILL.md`: the role models, the dispatcher effort and `agents.executor` read through `solo-sdd config get`, the fixed `opus` and `/effort low` kept as the defaults; rows in `tests/test_skill_commands.py` named after Subagent model settings and Executor setting from the owner fail first and then pass
- [ ] 1.5 `global/AGENTS.md` (sections 7 and 10) and `ALGORITHM.md` name `agents.test-model`, `agents.executor` and the rule that an agent changes `agents.executor` only on the owner's words; rows in `tests/test_skill_commands.py`; `docs/settings.md` rows; `tests/stands/settings-tui.py` gains the rows, every assertion kept
- [ ] 1.6 The stand `tests/stands/settings-agent-models.py` runs steps 2-5 of the Live Scenario

## 2. Acceptance

- [ ] 2.1 Run the Live Scenario (or its Fallback) from verification.md and record the Result, Not Verified and Decisions Without Owner sections
- [ ] 2.2 Run `solo-sdd validate settings-agent-models` and archive the change with `solo-sdd archive settings-agent-models --yes`
