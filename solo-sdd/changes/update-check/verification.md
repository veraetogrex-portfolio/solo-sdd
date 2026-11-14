## Live Scenario

The stand `python3 tests/stands/update-check.py` uses a temporary `HOME`, a local HTTP server standing in for PyPI and npm (its address given through the registry address variable the module reads, used by the tests only), and a virtual environment at `$T/.local/share/uv/tools/solo-sdd` holding a wheel built from the tree with version `0.2.0`, so the install method is uv; a fake `uv` on `PATH` installs a second wheel built with version `0.3.0` into that environment. The menu is driven through a pseudo-terminal at 120x40 and 40x12, with colours and with `NO_COLOR=1`.

| Element | Action | Expected result |
|---|---|---|
| home menu, server answers `0.3.0` | open | the menu draws before the answer; then the header shows `0.3.0 available` |
| `solo-sdd doctor` | run | `warn version:` with `uv tool upgrade solo-sdd` |
| home menu again within 24 hours, server stopped | open | the notice from the cache, no request in the server log |
| `solo-sdd list`, `solo-sdd validate --all`, `solo-sdd config get mode` with the cache made stale | run | no request in the server log |
| server answers `0.3.0\u001b[2J; rm -rf ~`, then a 2 MB body, then `{"info": 5}` | open the menu with a stale cache each time | no notice, the cache holds no part of the answer, the screen is not cleared |
| Update to `0.3.0` | Enter, then cancel | the command `uv tool upgrade solo-sdd` and the link to the `v0.3.0` release shown; the fake `uv` log stays empty |
| Update to `0.3.0` in a project whose rules block is from the older rules | Enter, confirm, confirm `solo-sdd init` | the fake `uv` ran once, `solo-sdd --version` of the environment prints `0.3.0`, `solo-sdd status` shows the `0.3.0` layout, `doctor` prints `ok project-rules:`, the menu asks to restart |
| fake `uv` exiting 1 | confirm the update | its output is shown, the layout stays `0.2.0` |
| Skip this version | pick it, reopen with `0.3.0`, then with `0.3.1` | no notice, then `0.3.1 available` |
| `SOLO_SDD_NO_UPDATE_CHECK=1` | open the menu, run `doctor` | no request; `ok version:` naming the check as off |
| update check switch of the Machine section | turn off, reopen | no request |

Then once on the real registry, with the owner's network: `solo-sdd doctor | grep version` on this machine prints the PyPI answer for `solo-sdd`.

## Needs

none

## Fallback

The last step needs the network; without it, the stand's local server stands in and the step is named in Not Verified.

## Result

<!-- Filled during apply: date, what was run, what was observed. -->

## Not Verified

<!-- Filled during apply: what stayed unproven and why. Write: nothing - if all proven. -->

## Decisions Without Owner

- plan: update on launch was asked → an automatic check and an update on confirmation, never a silent upgrade — a silent upgrade rewrites the agents' folders mid-session and may pick the wrong one of five install methods
- plan: the check runs only in the home menu and `doctor` → agents and hooks call the other commands constantly and must not wait on the network
- plan: the update also lays out the new version and offers to refresh the current project's rules block → an upgraded package with old copies or old project rules is a half update
