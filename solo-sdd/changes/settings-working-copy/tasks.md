## 1. Implementation

- [ ] 1.1 Rows in `tests/test_settings.py` named after Working copy settings and Working copy items as the old source: the seven keys with type and default, each old item read with `source: AGENTS.md` ("Orchestrators:" as `dispatch.limit`, "Loopback: needed" from "Working copy" and from "Commands" as `on`), a refused item value named on stderr with `AGENTS.md:<line>` and not taken, the file winning; they fail first
- [ ] 1.2 The keys in the settings block with `ABOUT` lines and the `AGENTS.md` items read as the old source in the block next to the "Delivery" reader; `python3 scripts/sync_blocks.py --check` empty; the rows of 1.1 pass
- [ ] 1.3 `global/sdd_worktree.py` takes paths, prepare, after refresh and links from the settings (a `node_modules` item found up to three levels as today, another item linked at its path from the root, every item added to `info/exclude`); rows in `tests/test_sdd_worktree.py` with config values and no section, and with `worktree.links: node_modules, vendor/bundle`, fail first and then pass, existing tests keep every assertion
- [ ] 1.4 `global/sdd_dispatch_plan.py` takes shared paths, the limit and loopback from the settings, `global/sdd_dispatch.py` the check timeout below a valid `SDD_DISPATCH_TIMEOUT` (an invalid variable falls to the setting, a setting above 2147483 s is used as 2147483); rows in `tests/test_sdd_dispatch_plan.py` and `tests/test_sdd_dispatch.py` fail first and then pass
- [ ] 1.5 `skills/project-init/SKILL.md` divides by `dispatch.limit` through `solo-sdd config get`, takes a `worktree.` or `dispatch.` key in the file as the dispatcher sign, and writes new working copy values through `solo-sdd config set` instead of a new "Working copy" section; `skills/spec-dispatch/SKILL.md` names the keys; rows in `tests/test_skill_commands.py` named after Test command under dispatcher and Working copy values in the settings
- [ ] 1.6 `docs/settings.md` rows; `tests/stands/settings-tui.py` gains the rows, every assertion kept; the stand `tests/stands/settings-working-copy.py` runs the Live Scenario

## 2. Acceptance

- [ ] 2.1 Run the Live Scenario (or its Fallback) from verification.md and record the Result, Not Verified and Decisions Without Owner sections
- [ ] 2.2 Run `solo-sdd validate settings-working-copy` and archive the change with `solo-sdd archive settings-working-copy --yes`
