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
