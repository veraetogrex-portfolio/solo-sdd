## Live Scenario

The stand `python3 tests/stands/settings-tui-lists.py` runs `solo-sdd settings` through a pseudo-terminal in a temporary git repository after `solo-sdd init --yes`, with a project integration `demo-check` under `solo-sdd/integrations/` and a broken one `bad-check`, at terminal sizes 120x40 and 40x12, with colours and with `NO_COLOR=1`.

| Element | Action | Expected result |
|---|---|---|
| Integrations section | open it | `antislop` and `security-audit` bundled enabled, `demo-check` project disabled, `bad-check` with its reason |
| `antislop` | toggle, save, confirm | `integrations.off: antislop` in the config; `solo-sdd integrations list` shows it disabled; `AGENTS.md` equals a second copy of the project after `solo-sdd integrations disable antislop` |
| `demo-check` | toggle, save, confirm | `integrations: demo-check`; the `AGENTS.md` block holds its rules |
| `bad-check` | toggle | nothing changes, the reason stays shown |
| `demo-check` with `AGENTS.md` made read-only | toggle, save, confirm | the reason is shown; `solo-sdd/config` and `AGENTS.md` keep their bytes |
| Checklists section | add `money-safety`, paths `billing/**`, file `docs/checklists/money.md`, save | both keys in the config; the item is marked file missing |
| Checklists section | add `Money Safety` | the allowed characters are named, nothing added |
| `money-safety` | edit paths to `billing/**, src/pay/*.py`, save | the paths line changes, the file line keeps its bytes |
| `money-safety` | remove, save | neither key in the config |
| config with only `checklist.docs.paths` | open the section | `docs` marked incomplete, `file` named |

## Needs

none

## Fallback

Not needed: the stand runs locally through a pseudo-terminal.

## Result

<!-- Filled during apply: date, what was run, what was observed. -->

## Not Verified

<!-- Filled during apply: what stayed unproven and why. Write: nothing - if all proven. -->

## Decisions Without Owner

- analyze: the raw keys `integrations` and `integrations.off` stayed text keys of `settings-tui`, a second path that skips the `AGENTS.md` block → Enter on them opens the section — one path, one result
- analyze: Same result as the command is a statement for any project → a property test, not only rows
