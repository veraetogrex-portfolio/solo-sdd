## Live Scenario

The stand `python3 tests/stands/cli-menu.py` runs bare `solo-sdd` through a pseudo-terminal at 120x40 and 40x12, with colours and with `NO_COLOR=1`, in temporary git repositories.

| Element | Action | Expected result |
|---|---|---|
| `solo-sdd < /dev/null` | run | the command list, exit code 2 (not through the pseudo-terminal) |
| home menu in a project with two open changes | open | the folder, the version, the mode and `2 open changes` in the header; the seven entries |
| Project settings | Enter | the settings screen of `settings-tui`; `q` returns to the menu |
| Integrations and checklists | Enter | the sections of `settings-tui-lists`; `q` returns |
| Machine | Enter | the section of `settings-tui-home`; `q` returns |
| Changes | Enter | the two rows of `solo-sdd list` with progress and `CLAIM`; no key edits them |
| Doctor | Enter | the `doctor` lines; `q` returns |
| Commands | Enter | the command list; `q` returns |
| Quit | Enter, or `q` on the menu | the process exits with code 0 and the terminal echoes input again |
| menu in a git repository without `solo-sdd/` | Prepare this folder, Enter on every question | `solo-sdd/config` written as `solo-sdd init --yes` writes it in a copy of the repository; the menu shows the project entries |
| menu in a folder that is not a git repository | Prepare this folder | `not a git repository: git init` shown, nothing written, the menu stays |
| menu in a folder with only `openspec/` | open | `solo-sdd import openspec` named; the folder keeps its files and bytes |

## Needs

none

## Fallback

Not needed: the stand runs locally through a pseudo-terminal. A person opens `solo-sdd` once by hand in Terminal.app and walks the entries.

## Result

<!-- Filled during apply: date, what was run, what was observed. -->

## Not Verified

<!-- Filled during apply: what stayed unproven and why. Write: nothing - if all proven. -->

## Decisions Without Owner

- analyze: Prepare this folder outside a git repository was not described → the `init` refusal is shown and the menu stays — `init` already refuses there
- analyze: the Entry point test planned a stub of the menu → dropped; the stand proves the menu opens on a terminal and the existing rows prove the command list without one — doubles only for external I/O
