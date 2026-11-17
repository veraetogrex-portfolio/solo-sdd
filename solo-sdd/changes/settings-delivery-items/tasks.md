## 1. Implementation

- [x] 1.1 Rows in `tests/test_settings.py` named after Text settings: a title rule with spaces kept, a line break, a control character and 201 characters refused with the file unchanged, `describe` names the kind; they fail on the current code
- [x] 1.2 The kind `text` in the settings block of `solo_sdd/settings.py` (`check_value`, `KIND_TEXT`) and the keys `delivery.pr-title`, `delivery.deploy`, `delivery.owner-only` with their `ABOUT` lines; `python3 scripts/sync_blocks.py` copies the block, `--check` prints nothing, the rows of 1.1 pass
- [x] 1.3 Rows in `tests/test_settings.py` named after Delivery items in config and Defaults by mode: each item read from "Delivery" with `source: AGENTS.md`, a 240-character "Deploy:" item kept as written, the file value wins; they fail first; then `agents_delivery` reads the three items; the rows pass and the existing Defaults by mode rows keep every assertion
- [x] 1.4 Rows in `tests/test_sdd_pr.py` named after Owner-only paths gate: owner paths from the main folder's config (a WORKTREE config with fewer paths changes nothing), a PR editing `solo-sdd/config` gives code 8, broken main-folder settings give code 1 without a merge request; rows in `tests/test_sdd_dispatch.py` for land-local: a branch changing a config owner path or `solo-sdd/config` gives code 8, main unchanged; they fail first; then `global/sdd_pr.py` and `global/sdd_dispatch.py` land-local take the paths from the settings; the existing owner gate tests keep every assertion and pass
- [x] 1.5 `solo_sdd/settings_ui.py`: a `text` key is edited as a one-line input, Esc keeps the old value; a row in `tests/test_settings_ui.py` proves it
- [x] 1.6 `skills/ship/SKILL.md`, `skills/spec-dispatch/preparation.md`, `skills/spec-dispatch/merge.md`, `skills/project-init/SKILL.md`: the PR title, deploy and owner paths read through `solo-sdd config get`, the "Delivery" item named as the old source; rows in `tests/test_skill_commands.py` fail first and then pass
- [x] 1.7 `docs/settings.md` rows of the three keys and the `text` kind; `tests/stands/settings-tui.py` gains the three rows, every existing assertion kept; the stand `tests/stands/settings-delivery-items.py` runs steps 1-5 of the Live Scenario

## 2. Acceptance

- [ ] 2.1 Run the Live Scenario (or its Fallback) from verification.md and record the Result, Not Verified and Decisions Without Owner sections
- [ ] 2.2 Run `solo-sdd validate settings-delivery-items` and archive the change with `solo-sdd archive settings-delivery-items --yes`
