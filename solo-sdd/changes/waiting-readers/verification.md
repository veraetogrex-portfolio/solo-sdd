## Live Scenario

`python3 tests/stands/waiting-readers.py prepare` copies `tests/stands/next-up/project` into a fresh temporary folder as a git repository: its `docs/waiting.md` has four waiting rows in the first table (`dispatch-ci`, `add-import`, `release-040` and a `DESIGN.md` row), then `## Closed` holding the `publish-docs` row, then `## Run decisions`; `DESIGN.md` has every field filled, the Dial numbers too, next to `web/index.html`; the `WAITING` file of `publish-docs` is removed. It writes one prompt per skill (the laid-out text from this worktree, the folder, the ban on reading `tests/stands`, the answer form) and prints `copy:` and `prompt <skill>:`. Every answer comes from a `Lookup:` subagent of the lead session (`subagent_type: Explore`, `haiku`), never `claude -p`; the lead saves the answers into `tests/stands/waiting-readers/` only after all three runs.

0. `python3 sync.py status` → `outdated` for the edited copies of the skills, the global rules, `ALGORITHM.md` and the template in the agent folders, no `drift`; the runs below use the skill text of this branch through the prompts, and `sync.py push` is left to the delivery after merge (Deploy: no).
1. A subagent gets `prompt-context-resume.md` → the answer is kept as `tests/stands/waiting-readers/live-context-resume.md`; its Blockers line names none of the closed rows and all 4 waiting rows.
2. A subagent gets `prompt-blockers.md` (a new blocker of `add-export`) → kept as `tests/stands/waiting-readers/live-blockers.md`; its `docs/waiting.md` has one new row in the first table and the `## Closed` table unchanged.
3. A subagent gets `prompt-project-init.md` (a repeat run with every `DESIGN.md` field filled) → kept as `tests/stands/waiting-readers/live-project-init.md`; the `DESIGN.md` row is in `## Closed` with `DESIGN.md: no empty fields` and the date, not in the first table, and the other rows are kept. `python3 tests/stands/waiting-readers.py --grade tests/stands/waiting-readers/live-context-resume.md tests/stands/waiting-readers/live-blockers.md tests/stands/waiting-readers/live-project-init.md` prints `waiting readers: 6 of 6 checks pass`; `--grade-confined` on the three transcripts prints `grading out of reach: yes` (no tool input names `tests/stands/waiting-readers` or `tests/stands/next-up`); `clean <folder>` removes the copy.
4. The references: `python3 tests/stands/waiting-readers.py --grade tests/stands/waiting-readers/expected-context-resume.md tests/stands/waiting-readers/expected-blockers.md tests/stands/waiting-readers/expected-project-init.md` prints `waiting readers: 6 of 6 checks pass`; the same on the `old-*.md` answers (a closed row as a blocker, a row appended under `## Closed`, a deleted `DESIGN.md` row) prints `context-resume closed rows as blockers: 1`, `blockers new rows in first table: 0`, `project-init design row moved to Closed: no` and `waiting readers: 2 of 6 checks pass`; `--grade-confined tests/stands/next-up/leaked.jsonl` prints `grading out of reach: no`, on `tests/stands/next-up/confined.jsonl` `yes`.

## Needs

none

## Fallback

Not needed: the fixture is local.

## Result

<!-- Filled during apply: date, what was run, what was observed. -->

## Not Verified

<!-- Filled during apply: what stayed unproven and why. Write: nothing - if all proven. -->

## Decisions Without Owner

<!-- Filled during apply: choices made without asking, and new changes created for out-of-scope work. -->
