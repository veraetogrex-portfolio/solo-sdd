## Live Scenario

All against a fake `gh` on `PATH` that logs its arguments, in a temporary git project with `solo-sdd/`:
1. `delivery.ci-timeout: 3600` → `sdd-pr.py wait <url> --interval 1` stderr names `timeout 3600 s (file)`; with `--timeout 2` it names `timeout 2 s (flag)` and gives up after about 2 s.
2. `delivery.require-ci: off`, the fake PR with no checks and no required check → `wait` prints `CI: none` with code 0, `merge <url> squash <hash>` exits 0 and the log has the merge request; one red check → `CI: red`, `merge` exits 1.
3. `delivery.code-scanning: warn` with one open alert → `CI: green` and the alert line, code 0; `merge` puts the merge request into the log.
4. `delivery.draft: on` → `open` logs `pr create --draft`; `merge` logs `pr ready` before the merge request. `delivery.delete-branch: off` → no branch delete in the log.

All in one call: `python3 tests/stands/settings-ci-wait.py` → `4 of 4 checks passed`.

## Needs

none

## Fallback

not needed.

## Result

<!-- Filled during apply: date, what was run, what was observed. -->

## Not Verified

<!-- Filled during apply: what stayed unproven and why. Write: nothing - if all proven. -->

## Decisions Without Owner

- analyze: the new settings change what main `pr-tool` requirements state as fixed (no checks refused, every alert gives code 8, the branch always deleted, the 300 s and 1200 s limits) without MODIFIED → a `pr-tool` delta MODIFIES PR merge, Required checks in CI wait, Ship and land, Land after green and Code scanning in CI wait, every old scenario kept and the defaults named — a delta that contradicts the main spec without MODIFIED is CRITICAL.
- analyze: `require-ci: off` and `code-scanning: off` weaken merge gates, and nothing said who may set them → a requirement reads them only from the main folder's `solo-sdd/config`, and the change depends on `settings-delivery-items`, whose gate makes a PR editing `solo-sdd/config` wait for the owner; rejected: a second copy of that gate here, which would make two changes modify Owner-only paths gate.
- analyze: `require-ci: off` with a required check in the branch rules and no PR checks had no outcome → `infra` "required check did not start", `none` only when the base branch requires no check — the branch rules stay stronger than a project setting.
- analyze: the new result `none` had no reader in `spec-dispatch` → `merge.md` lands on `none` as on `green`, `report.md` shows `none`; both are in Impact and task 1.7.
- analyze: the output of `code-scanning: warn` was not named → `CI: green`, the alert lines, code 0; `off` prints no alert line — the dispatcher then lands as on `green`.
- analyze: the "first output line" with the limits would change the stdout the dispatcher reads → the limits line goes to stderr, stdout unchanged.
- analyze: `land` was named as taking the CI limits, but it does not wait for CI → only `wait` and `ship` take them.
- analyze: a draft PR and the code 8 gates → the ready request goes after every gate, right before the merge request; under `merge-by: human`, an owner path or a checklist the PR stays a draft and the person marks it ready; `ship` creates drafts too, since it opens the PR through the same step.
- analyze: `delivery.delete-branch` could be read as covering `land-local` → it covers PR delivery only, `land-local` keeps deleting the branch (`settings-local-merge`).
- analyze: a stuck or no-checks limit above `delivery.ci-timeout` → the whole timeout still ends the wait, as `min()` does today.
