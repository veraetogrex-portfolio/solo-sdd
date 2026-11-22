=== docs/waiting.md
# Waiting

What cannot be closed without an external condition. Only the first table waits: when the condition is met, the row moves to the table under `## Closed`, right after this table, with its evidence and the date (`/next-up` does it when it finds the evidence); a row is never deleted.

| Change | Items | Waiting for | From whom | Since |
| --- | --- | --- | --- | --- |
| dispatch-ci | 2.2 | a `/spec-dispatch` run in mode `pr` gets a red CI: its line in `docs/dispatch-log.md` | dispatcher | 2026-10-25 |
| add-import | 1.4 | the owner's decision on the CSV dialect | owner | 2026-11-02 |
| release-040 | 3.1 | the GitHub release v0.4.0 is published | owner | 2026-11-10 |

## Closed

| Change | Items | Waiting for | From whom | Since | Evidence | Closed |
| --- | --- | --- | --- | --- | --- | --- |
| — | — | DESIGN.md: fill in the fields Fonts, Dial | owner | 2026-11-05 | DESIGN.md: no empty fields | 2026-11-22 |
| publish-docs | 2.1 | the GitHub release v0.3.0 is published | owner | 2026-10-20 | gh release list: v0.3.0 Latest v0.3.0 | 2026-11-15 |

## Run decisions 2026-11-18 09:16

- add-export: launch now (key: launch)

=== report
Step 5a (DESIGN.md), project /var/folders/1y/vs_9dysd59d3dz68316ylvnc0000gn/T/waiting-readers.adnl5nc7/project:

- Interface: web/index.html exists outside the excluded folders, so the project has an interface and DESIGN.md applies. I checked the default extension list only; I did not run `solo-sdd config get ui.extensions`.
- DESIGN.md already exists (written by the user). All fields have answers: Character, Audience, Palette, Fonts (Inter), Mood (focused), Themes (light), and Dial with numbers (ENERGY 1 / RHYTHM 2 / MOTION 1). No field is empty, so DESIGN.md is kept unchanged.
- Because no fields are empty, the waiting row "DESIGN.md: fill in the fields Fonts, Dial" (from 2026-11-05) moves to `## Closed` with evidence "DESIGN.md: no empty fields" and closed date 2026-11-22. The row is kept, not deleted. The new file is above.
- The "Run decisions" section is unchanged.
- Not done: this session cannot write, so docs/waiting.md is only returned here for the caller to apply. AGENTS.md and the other steps were not touched, as the prompt requires.
- Read scope: only files inside the project folder (AGENTS.md, DESIGN.md, docs/waiting.md, and directory listings). I did not read the templates folder, tests/stands, or anything outside the project.
