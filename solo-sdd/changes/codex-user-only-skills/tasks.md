## 1. Implementation

- [ ] 1.1 Requirement User-only skills in Codex (ADDED): add to `tests/test_skill_commands.py` one table-driven test over `skills/*/SKILL.md` that reads the frontmatter and `agents/openai.yaml` with its `targets.json` entry, with rows for the scenarios A new user-only skill without the file, A model-invoked skill with the policy, A user-only skill with the wrong policy and A file not laid out, and an assertion that `docs/layout.md` names `agents/openai.yaml` and `allow_implicit_invocation`, built in a temporary copy the way the existing step-file tests build theirs; proven by `python3 -m unittest test_skill_commands` from `tests/` failing on the current code and naming the seven skills
- [ ] 1.2 Write `agents/openai.yaml` holding exactly the two lines `policy:` and `  allow_implicit_invocation: false` (the block form of the Codex documentation; the test reads the file as text lines, so a quoted `"false"`, `False`, `no` or a flow mapping fails it) in the folders of `blockers`, `changes`, `health`, `next-up`, `relay`, `report` and `review-principles`; proven by the test of 1.1 passing for these rows
- [ ] 1.3 Add to `targets.json` one `files` entry per new file, `{"skills": {"<name>": "agents/openai.yaml"}}`, the form the step files of `spec-dispatch` use; proven by the row A file not laid out passing and by `python3 sync.py push` into a temporary `HOME` with an empty `~/.codex` folder giving the files of the scenario The layout
- [ ] 1.4 Name the file in `docs/layout.md`: what it holds, that Codex reads it to keep the skill manual, and that it pairs with `disable-model-invocation`; proven by the `docs/layout.md` assertion of the test of 1.1 passing
- [ ] 1.5 Run `python3 tests/run.py --jobs 5 --tier slow`, the lint and `python3 -m solo_sdd validate --all`; proven by `failed: 0`, no lint output and 0 errors

## 2. Acceptance

- [ ] 2.1 Run the Live Scenario (or its Fallback) from verification.md and record the Result, Not Verified and Decisions Without Owner sections
- [ ] 2.2 Run `solo-sdd validate codex-user-only-skills` and archive the change with `solo-sdd archive codex-user-only-skills --yes`
