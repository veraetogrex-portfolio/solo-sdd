## 1. Implementation

- [ ] 1.1 Rows in `tests/test_settings.py` named after Branch and commit prefixes and Prefix change guard: defaults, `describe`, refusal by `set` and `unset` with a leftover branch of an open change and the file unchanged, a branch of an archived change allowed, equal prefixes and `feat/*` refused; a Hypothesis property `test_prefix_change_guard_property` over generated prefixes (slashes, dots, `*`, `~`, a trailing `/`, `@{`): `config set` either exits 1 with the file unchanged or `git check-ref-format --branch <prefix>a` accepts the name, and it fails on a mutant without the ref check; the value strategies of the Config command property gain the three keys; they fail first
- [ ] 1.2 The three keys in the settings block of `solo_sdd/settings.py` with `ABOUT` lines (group `delivery` for the branch prefixes, `process` for the light prefix) and the guard in `run` of `solo_sdd/settings.py` and in `solo_sdd/settings_ui.py`; a row in `tests/test_settings_ui.py` for the screen refusal fails first; `python3 scripts/sync_blocks.py --check` empty; the rows of 1.1 and this row pass
- [ ] 1.3 `global/sdd_dispatch_plan.py` and `global/sdd_dispatch.py` take the branch prefix; rows in `tests/test_sdd_dispatch_plan.py` (the team prefix scenario) and `tests/test_sdd_dispatch.py` with `feat/` fail first and then pass, existing tests keep every assertion
- [ ] 1.4 `global/sdd_pr.py` (the local branch cleanup) and `global/sdd_eval.py` take the branch prefix; rows in `tests/test_sdd_pr.py` and `tests/test_sdd_eval.py` with `feat/` fail first and then pass
- [ ] 1.5 `skills/spec-dispatch/SKILL.md`, `merge.md`, `report.md`, `orchestrator-prompt.md`, `skills/spec-plan/SKILL.md` and `skills/spec-plan/plan-commit.md` read the prefixes through `solo-sdd config get`; `grep -rn 'change/<\|plan/<' skills` prints no line without `delivery.branch-prefix` or `delivery.plan-prefix` on it; rows in `tests/test_skill_commands.py`
- [ ] 1.6 `global/AGENTS.md`, `ALGORITHM.md` (the light commit and the plan branch), `skills/spec-plan/SKILL.md`, `skills/work-status/SKILL.md`, `skills/report/SKILL.md` name `commit.light-prefix` with the default `light:`, matched as plain text; rows in `tests/test_skill_commands.py` fail first and then pass
- [ ] 1.7 `docs/settings.md` and `docs/layout.md` rows; `tests/stands/settings-tui.py` gains the rows, every assertion kept; the stand `tests/stands/settings-branch-names.py` runs steps 1-3

## 2. Acceptance

- [ ] 2.1 Run the Live Scenario (or its Fallback) from verification.md and record the Result, Not Verified and Decisions Without Owner sections
- [ ] 2.2 Run `solo-sdd validate settings-branch-names` and archive the change with `solo-sdd archive settings-branch-names --yes`
