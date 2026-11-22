Goal: Continue the `shop` project (small web shop, tests via `python3 -m unittest`). The open work is change `add-export` (task 1.2, its test) and the blockers listed below. Work only in the project folder.

Source of truth: `/var/folders/1y/vs_9dysd59d3dz68316ylvnc0000gn/T/waiting-readers.adnl5nc7/project`: `AGENTS.md`, `solo-sdd/project.md` (Mode: demo), `docs/waiting.md`, `solo-sdd/changes/*/tasks.md`, `docs/dispatch-log.md`, `DESIGN.md`, git.

Last confirmed state (2026-11-22): branch `main`, HEAD `84d06f5` ("shop"), working tree clean. No `CLAUDE.md`, `docs/status.md`, or `handoff.md` exist. `solo-sdd list --json` was not run. `tests/stands` was not read, as instructed.

Decisions and constraints:
- `docs/waiting.md`: a row is never deleted. When its condition is met, it moves to `## Closed` with evidence and a date.
- `docs/waiting.md` run decision 2026-11-18: add-export, "launch now" (key: launch).
- `docs/backlog.md`: product search ignores accents ("cafe" vs "café"); cart total rounds three-decimal prices wrong. Both are unscheduled.

Blockers (first table of `docs/waiting.md` only):
- dispatch-ci, item 2.2: waiting for a `/spec-dispatch` run in mode `pr` to get a red CI (dispatcher). `docs/dispatch-log.md` already has `2026-11-12 10:41 dispatch-ci: CI: red`, so the condition looks met. Needs a closing row with evidence.
- add-import, item 1.4: owner's decision on the CSV dialect (owner, since 2026-11-02). No `add-import` change folder exists in `solo-sdd/changes`.
- release-040, item 3.1: GitHub release v0.4.0 is published (owner, since 2026-11-10). Not checked, because it needs `gh`, and there is no release-040 change folder locally.
- DESIGN.md fields Fonts and Dial (owner, since 2026-11-05). `DESIGN.md` now has `Fonts: Inter` and `Dial: ENERGY 1 / RHYTHM 2 / MOTION 1` filled in, so the condition looks met. Needs a closing row with evidence.

Closed: publish-docs, item 2.1 (v0.3.0 release, closed 2026-11-15). Note: `solo-sdd/changes/publish-docs/tasks.md` still shows 2.1 unchecked, which is a divergence.

Next step: Run `python3 -m unittest` in the project folder, then implement and check add-export task 1.2 (its test). Closing the two blockers whose evidence is already in the repo is for `/next-up`, not for this session.

History versus fact divergences:
- The waiting table lists DESIGN.md fields as open, but `DESIGN.md` has both fields filled in.
- The waiting table lists dispatch-ci as open, but `docs/dispatch-log.md` records a red CI on 2026-11-12.
- The `publish-docs` tasks file shows 2.1 unchecked while the row is under Closed.
- The run decision "add-export: launch now" (2026-11-18) is older than the current task state, where 1.2 is still open.
- No history was searched (skipped per instructions). No files were written and no long-running processes were started.
