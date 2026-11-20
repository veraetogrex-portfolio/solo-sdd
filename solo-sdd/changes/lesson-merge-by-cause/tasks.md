## 1. Rules

- [ ] 1.1 New test `test_short_lessons_merged_by_cause` in `tests/test_skill_commands.py`, reading section 15 of `global/AGENTS.md` like `test_project_rules_through_config`, for `Lessons without duplicates` and `Short line with full text`: the section names a merge into one line about the shared cause, the 300-character bound and `LESSONS.md` under an id; it fails on the current text (`python3 tests/test_skill_commands.py`)
- [ ] 1.2 Section 15 of `global/AGENTS.md`: merge by the shared cause, one sentence of at most 300 characters, details under `### <id>` in the project's `LESSONS.md`, a longer line shortened in the same edit with its text kept; 1.1 passes
- [ ] 1.3 Shorten the four lines of this repository's `## Lessons` over 300 characters (`formats-read-like-their-program`, `setting-sources`, `input-edge-forms`, `ignored-paths`) to their cause; their full text in `LESSONS.md` is unchanged; a one-line `python3 -c` measuring each line before its link prints no line over 300

## 2. Stand

- [ ] 2.1 `tests/stands/lesson-stand/AGENTS.long.md`: 20 lessons, none about async calls, one of them a glued line over 1,000 characters holding the phrase `retries a paid call`; `check.sh` also prints `over 300: <n>`, `missing ids: <ids> | none` and `lost: <n>` (lines of the section in `git show HEAD:AGENTS.md` found neither in the current section nor verbatim in `LESSONS.md`; no git commit: `lost: n/a`); `README.md` gets the Live Scenario steps of this change
- [ ] 2.2 `tests/stands/lesson-routing.py`: `AGENTS.long.md` gives `20 lines`, `over 300: 1`, `missing ids: none`, `lost: 0` as committed and `lost: 1` after the glued line is deleted from a committed copy; a mutation of `check.sh` that drops the length count makes it fail (`/usr/bin/python3 tests/stands/lesson-routing.py`)

## 3. Deployment

- [ ] 3.1 `python3 sync.py push`, then `python3 sync.py status`: no unexpected `drift`, `~/.claude/CLAUDE.md` holds the new section 15 text

## 4. Acceptance

- [ ] 4.1 Run the Live Scenario (or its Fallback) from verification.md and record the Result, Not Verified and Decisions Without Owner sections
- [ ] 4.2 Run `solo-sdd validate lesson-merge-by-cause` and archive the change with `solo-sdd archive lesson-merge-by-cause --yes`
