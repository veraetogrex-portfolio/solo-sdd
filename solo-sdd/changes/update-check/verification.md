## Live Scenario

The stand `python3 tests/stands/update-check.py` uses a temporary `HOME`, a local registry standing in for PyPI: a named pipe under a `file://` address given through `SOLO_SDD_REGISTRY` (the registry address variable the module reads, used by the tests only) that logs each read as a request, and a virtual environment at `$T/.local/share/uv/tools/solo-sdd` holding the package laid out from the tree as the wheel lays it out, with version `0.2.0`, so the install method is uv; a fake `uv` on `PATH` replaces it with the same layout at version `0.3.0`. The menu is driven through a pseudo-terminal at 120x40 and 40x12, with colours and with `NO_COLOR=1`.

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
- apply: the stand's registry is a named pipe under `file://`, not an HTTP server on 127.0.0.1, and the package is laid out by copying the wheel's layout instead of building wheels → this session's sandbox refuses loopback connections (a proxy answers 403, a direct connect fails) and building a wheel needs `hatchling` from the network; the real HTTP path is checked once against pypi.org and registry.npmjs.org

- plan: update on launch was asked → an automatic check and an update on confirmation, never a silent upgrade — a silent upgrade rewrites the agents' folders mid-session and may pick the wrong one of five install methods
- plan: the check runs only in the home menu and `doctor` → agents and hooks call the other commands constantly and must not wait on the network
- plan: the update also lays out the new version and offers to refresh the current project's rules block → an upgraded package with old copies or old project rules is a half update
- analyze: whether a failed request counts toward the once in 24 hours → every attempt stores its time; a failure keeps the last checked version and stores a fixed reason word, never the answer's text — offline, each launch would otherwise wait 2 seconds
- analyze: the Machine section of `solo-sdd settings` shows the doctor rows → it shows the version line from the cache only and makes no request — `settings` is a command other than the home menu and `doctor`
- analyze: whether a skipped version still warns in `doctor` → `doctor` warns about any newer version; Skip hides only the menu notice — `doctor` is the check a person runs on purpose
- analyze: how the update check switch of the Machine section is applied → Space saves it at once in the cache file, outside the `a` plan — it runs no install or uninstall command
- analyze: where the update steps run → off the full screen, like Prepare this folder, so their output streams to the terminal; after success solo-sdd asks to restart and exits — the menu in memory is still the old program
- analyze: the release notes link → `https://github.com/veraetogrex-portfolio/solo-sdd/releases/tag/v<version>`, the Repository URL of `pyproject.toml` kept in one constant — an npm install carries no Python package metadata to read it from
- analyze: hooks and the request → the deployed hooks are standalone scripts that import no `solo_sdd` module, so they cannot reach the request; the property test covers the CLI commands
