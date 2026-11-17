## Live Scenario

1. In a temporary git project with `solo-sdd/` and "Delivery" holding "Owner only: `docs/**`": `python3 -m solo_sdd config get delivery.owner-only` → `docs/**`, `source: AGENTS.md`.
2. `python3 -m solo_sdd config set delivery.pr-title "<id>: <summary>"` → code 0; `config get delivery.pr-title` → `<id>: <summary>`, `source: file`; `config set delivery.deploy` with 201 characters → exit 1 naming `at most 200 characters`.
3. `python3 -m solo_sdd config describe delivery.pr-title` → group `delivery`, type `text: one line, at most 200 characters`.
4. With a fake `gh` that returns a green PR changing `deploy/prod.yml`, and `delivery.owner-only: deploy/**` in the file: `sdd-pr.py merge <url> squash <hash>` → code 8 `waits for the owner: deploy/prod.yml`, no merge request in the fake `gh` log.
5. The same with a PR that changes `solo-sdd/config` → code 8 naming `solo-sdd/config`.
6. `python3 tests/stands/settings-tui.py` → passes and lists the three keys.

Steps 1-5 in one call: `python3 tests/stands/settings-delivery-items.py` → `5 of 5 checks passed`.

## Needs

none

## Fallback

not needed.

## Result

<!-- Filled during apply: date, what was run, what was observed. -->

## Not Verified

<!-- Filled during apply: what stayed unproven and why. Write: nothing - if all proven. -->

## Decisions Without Owner

- analyze: the new keys take an `AGENTS.md` source that the main requirement Defaults by mode allows only for `delivery.mode` and `delivery.merge` → Defaults by mode is MODIFIED to name "the key's old source", the item its requirement names, with the same three scenarios — a delta that contradicts the main spec without MODIFIED is CRITICAL, and the general wording also fits the later `settings-working-copy` and `settings-project-rules` sources.
- analyze: the gate text did not say whose `solo-sdd/config` gives the owner paths → the main folder's, never the PR's or the WORKTREE's — a PR must not shorten its own gate, as with the "Owner only:" item today.
- analyze: "an unreadable source means only `.github/workflows/**`" contradicted Settings file and Base branch from settings, where broken settings exit 1 → broken settings give code 1 without a merge request, an unreadable `AGENTS.md` drops only its own item; rejected: falling back to fewer paths, which opens the gate on a typo.
- analyze: task 1.4 changed land-local with no test row → land-local rows in `tests/test_sdd_dispatch.py` (config owner path, `solo-sdd/config` edit, code 8) — a task needs an observable criterion.
- analyze: an old "PR title:" or "Deploy:" item may be longer than 200 characters or hold backquotes → the text after the label is taken trimmed and as written; the 200-character limit holds only for a value set in the file — refusing it would break `config get` in projects that work today.
