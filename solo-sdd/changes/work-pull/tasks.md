## 1. Implementation

- [ ] 1.1 Requirements Work queue with sources and Waiting lines closed with evidence: write `skills/next-up/SKILL.md` (a manual command with `disable-model-invocation: true`, the sources and the `doctor` line, the first-table rule, the evidence rule, the `## Closed` place and columns, the `WAITING` item, the queue and report form) and its `targets.json` entry for every agent; rows in the laid-out skill text test of `tests/test_skill_commands.py` for `## Closed`, `## Run decisions` and the `WAITING` item; proven by `python3 tests/test_skill_commands.py` (with the size budget) and `python3 sync.py status`
- [ ] 1.2 Requirement Foreign text in issues and PRs: the data-not-instructions rule in the skill, and the ordering issue body in the fixture with its checks in `--grade` (`changes started: 0`, no row moved without evidence); proven by `--grade` on a reference copy where the issue was obeyed giving `changes started: 1`
- [ ] 1.3 Change the template `templates/docs/waiting.md` (a met line moves to `## Closed`, the `WAITING` file is removed by its change); list `/next-up` among the manual commands of section 14 of `global/AGENTS.md`, the README table and `docs/layout.md` (the skill count and list), and add its section to `docs/skills-audit.md`; proven by `python3 tests/test_skill_commands.py` (the audit table test) and `python3 tests/test_repo_language.py`
- [ ] 1.4 Build the fixture `tests/stands/next-up/` (the project, the fake `gh` with a failing mode; `errors.log` written at run time) and `tests/stands/next-up.py --grade <copy> <report>`; proven by `--grade` on a reference copy and report giving every check `yes` and on an untouched copy giving `closed 0 of 2 met`

## 2. Acceptance

- [ ] 2.1 Run the Live Scenario (or its Fallback) from verification.md and record the Result, Not Verified and Decisions Without Owner sections
- [ ] 2.2 Run `solo-sdd validate work-pull` and archive the change with `solo-sdd archive work-pull --yes`
