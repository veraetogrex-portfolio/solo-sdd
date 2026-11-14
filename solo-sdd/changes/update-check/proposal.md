# Proposal

## Why

The owner asked whether the CLI watches for updates and updates itself on launch. Today it does neither: `solo-sdd update` lays out the installed version again and prints the upgrade command of the install method; nothing tells a person that a newer version exists, so the skills, hooks and rules on the machine silently fall behind. An upgrade also leaves every prepared project's rules block at the old version (named by `doctor` after `project-rules-stale`).

A silent upgrade on every launch is not taken: it would rewrite the agents' folders in the middle of their sessions, pick one of five install methods (uv, pipx, npm, a clone, pip) and could break the wrong one, and make the version on the machine unpredictable. The check is automatic, the upgrade happens on the person's confirmation.

## What Changes

- Design Read: update notice and update step of the home menu for not specified, not specified, ENERGY 1 / RHYTHM 1 / MOTION 1 draft without direction
- A version check: the home menu (in the background, never delaying it) and `doctor` ask the registry of the install method (npm for an npm install, PyPI otherwise) for the latest stable version, at most once in 24 hours, with a 2 second timeout, caching the answer and its time in `~/.local/share/solo-sdd/update-check.json`. A clone is never checked. Every other command and every hook stays off the network.
- The registry answer is checked: at most 1 MB, JSON of the expected shape, a version of the form `N.N.N` in ASCII digits; anything else is no answer. Only a version newer than the installed one is a notice.
- `doctor` prints a `version` line: the latest, or a newer version with the upgrade command, or the reason the latest is unknown.
- The home menu header shows the notice and gains the entry Update to `<version>`: it shows the upgrade command of the install method (a fixed command; no registry text enters a command) and the release notes link, runs it only after confirmation, then runs `solo-sdd install` from the upgraded program, then in a project offers `solo-sdd init` when `doctor` names the rules block as older, and asks to restart `solo-sdd`. A failed step shows its output and runs nothing after it.
- Skip this version hides the notice until a newer one; `SOLO_SDD_NO_UPDATE_CHECK=1` or the update check switch of the Machine section turns the check off.

## Capabilities

### New Capabilities
- `update-check`: the version check and the confirmed update from the home menu.

### Modified Capabilities

## Impact

- `solo_sdd/update_check.py` (new), `solo_sdd/doctor.py`, `solo_sdd/settings_ui.py`, `solo_sdd/cli.py`
- `docs/cli.md`, `README.md` (the update section)
- `tests/test_update_check.py` (new), `tests/stands/update-check.py` (new), `tests/affected.json`

## Out of Scope

- The stale rules line of `doctor`: `project-rules-stale`.
- The menu and the screens themselves: `cli-menu`, `settings-tui`, `settings-tui-lists`, `settings-tui-home`.
- Upgrading without a confirmation, on launch or on a schedule.
- Pre-release versions and pinning a version other than the latest.
- Refreshing other projects than the current folder.

## Depends On

cli-menu, project-rules-stale

## Source

The owner, 2026-11-14 (translated from Russian): "Will the CLI watch for updates and update the version on launch?", then: "Yes, add it. Think ahead, damn it, about how to make it better".
