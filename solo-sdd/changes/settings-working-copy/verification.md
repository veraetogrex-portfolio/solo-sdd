## Live Scenario

In a temporary main repository with `solo-sdd/` and no "Working copy" section:
1. `config set worktree.prepare "touch prepared"` and `config set worktree.links node_modules` → `python3 global/sdd_worktree.py setup <MAIN> <WORKTREE>` → the summary line names the command, `<WORKTREE>/prepared` exists, `node_modules` is a link and `.venv` is not.
2. Add "Working copy" with "Shared: `CHANGELOG.md`" and "Orchestrators: 4" and no file value → `config get dispatch.shared` → `CHANGELOG.md`, `source: AGENTS.md`; `python3 global/sdd_dispatch_plan.py <MAIN>` prints `limit: 4` and `config get dispatch.limit` prints `4`.
3. `dispatch.check-timeout: 900` and `SDD_DISPATCH_TIMEOUT=1` with a check `sleep 5` in `land-local` → `timeout after 1 s`.
4. `dispatch.loopback: on`, no "Loopback:" item → `python3 global/sdd_dispatch_plan.py <MAIN>` run under `sandbox-exec -p '(version 1)(allow default)(deny network*)'` prints `loopback: blocked (needed by the project):`; with `dispatch.loopback: off` the same run prints `loopback: blocked:` without the suffix (macOS: `sandbox-exec` denies the loopback probe).

All in one call: `python3 tests/stands/settings-working-copy.py` → `4 of 4 checks passed`.

## Needs

none

## Fallback

not needed.

## Result

<!-- Filled during apply: date, what was run, what was observed. -->

## Not Verified

<!-- Filled during apply: what stayed unproven and why. Write: nothing - if all proven. -->

## Decisions Without Owner

- analyze: Depends On `settings-delivery-items` (the `text` kind and the old-source rule of Defaults by mode) is open, not archived → the change waits for it in the queue; no artifact edit — the intended order of the plan.
- analyze: `config get dispatch.limit` did not read "Orchestrators:" while the dispatch plan does, so `project-init` through `config get` would divide by 2 where the plan runs 4 → `dispatch.limit` takes the "Orchestrators:" item as its old source, scenario The old item still counts — every reader takes a setting from one shared definition.
- analyze: "Loopback: needed" is read from "Commands" too, and its value `needed` has no key value → it is `on` from either section — the current reader accepts both sections.
- analyze: an old item value the key refuses (the current reader drops absolute and `..` paths silently) → not taken, named on stderr with `AGENTS.md:<line>` — never skip silently, and a project keeps working.
- analyze: what a `worktree.links` item other than `node_modules` and `.venv` means → linked as one link at its path from the root, `node_modules` keeps its three-level search, every item goes to `info/exclude` — matches today's `.venv` handling.
- analyze: an invalid `SDD_DISPATCH_TIMEOUT` with a config value → the setting applies; a setting above 2147483 s is used as 2147483 — the variable already falls back on invalid input, and the limit guards the C int of the wait.
- analyze: task 1.5 had `project-init` write values through `config set` with no requirement → added Working copy values in the settings; the dispatcher sign became a "Working copy" section or a `worktree.` or `dispatch.` key in the file — a project that sets only `dispatch.limit` uses the dispatcher too.
- analyze: Live Scenario step 4 printed a `loopback:` line on any code → the step runs the plan with loopback denied by `sandbox-exec` (probed here: under it the bind to 127.0.0.1 fails with `Operation not permitted`; the suffix check holds whether or not loopback works outside it) and checks the `(needed by the project)` suffix only the new key produces.
- apply: a "Prepare:" or "After refresh:" item longer than 200 characters → taken as written, without the text limit — the documented rule of the text keys' `AGENTS.md` items (`delivery.deploy`), so a working project's long command is not dropped; paths and numbers are checked and refused.
- apply: several "Prepare:", "After refresh:" or "Orchestrators:" items → the first one counts (the old readers took the last) — the same as the Delivery items; several "Paths:" and "Shared:" items add up as before.
- apply: a "Shared:" value with a leading `/` → the `/` is dropped before the check, as the old reader and the `--shared` flag did; a "Paths:" value starting with `/` is refused, as the spec scenario says.
- apply: `config set worktree.prepare ""` → accepted as an empty value (not set): a text key whose default is empty takes an empty value, like the other keys with the default "".
- apply: a `worktree.links` item `vendor/bundle` whose parent folder does not exist in the worktree → the parent folders are created, so the named link is made; a found nested `node_modules` keeps today's rule (skipped without its parent).
- apply: `sdd-dispatch.py accept` keeps 600 s (or the variable): the spec names only `land-local` for the setting; `land-local` reads the setting once it reads the settings, so its first `git status` keeps 600 s.
- apply: `skills/spec-next/SKILL.md` and `docs/layout.md` still say "the paths of the Working copy section" and "node_modules and .venv": true for the defaults and an old section, not in this change's Impact, left as written.
- review round 1, Important "a links item without / excluded and skipped at any depth" → fixed: every item but `node_modules` goes to `info/exclude` as `/<item>` and is skipped only at its path from the root.
- review round 1, Important "remove and discard need valid settings" → fixed: setup records the folders it linked in `<WORKTREE>.links`; `remove` and `discard` unlink by that record (a worktree set up before it: the default `node_modules` and `.venv`) and never read the settings; the record goes with the worktree.
- review round 1, Important "the project-init limit has no fallback" → fixed: no `solo-sdd/` tree, no command or a failed call takes the first number of the "Orchestrators:" item, else 2; working copy values without a tree are named in the report, nothing written.
- review round 1, Important "tests repeat stand scenarios" → the repeated rows dropped (the variable-wins land-local half, the summary-line check, the loopback `on` row); the `dispatch.limit` row of `test_the_old_items` stays: it checks the first number after text, the first item and the section scope, which the stand does not.
- review round 1, Nits: the test message fixed; `loopback_needed` kept (an existing test reads it); the stale texts are outside the Impact (see above); the settings screen names the "Working copy item" also for a `Loopback: needed` of "Commands", one label for the group; a parent path part that is a file makes `setup` exit 1 with `error:` (an `OSError`), no traceback. Pre-existing: backquoted values inside code fences are read as items, as on main.
- review round 2, Important "a `./data` links item is linked but not excluded" → fixed where every worktree reader passes (`section()`): each `worktree.paths` and `worktree.links` item is read in one form (`./data`, `data/.`, `vendor//bundle` become `data`, `vendor/bundle`; `.` names no path).
- review round 2, Nit "the links record is written once" → fixed: the record is rewritten after each link and a repeated setup adds to it.
- review round 2, Nit "the test cannot show the record chose what was unlinked" → kept as is: git removes a leftover link either way, the difference is not observable from outside.
- review round 2: the round 1 withdrawal of the `test_the_old_items` part of the test finding is accepted; the other open Nits stay as recorded in round 1.
