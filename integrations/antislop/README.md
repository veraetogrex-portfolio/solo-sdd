# Pinned copy of anti-slop

A copy of the anti-slop rules (https://github.com/miqdadbadjuber/anti-slop), MIT license in `LICENSE`. Used by the `ui-check` and `copy-check` skills.

Origin: the release and commit are recorded in `VERSION` (two lines).

Taken: `antislop.md`, `skills/antislop-ui`, `skills/antislop-human` (without `contrast-mcp.py`), `skills/antislop-layoutmobile`, `skills/antislop-copywriting`. Not taken: `contrast-mcp.py`, `antislop-code`, the installer, plugins.

Deployment: `sync.py push` by `targets.json["files"]` puts the files into `<root>/ui-check/antislop/` as `core.md`, `ui.md`, `human.md`, `layoutmobile.md`, `contrast-check.py`, `references/…` and into `<root>/copy-check/antislop/` as `core.md` (the same core) and `copywriting.md`. Licenses, `README.md` and `VERSION` are not deployed.

Updating: replace the copy whole with the files of a new release, update `VERSION`, keep the diff in the commit, run `python3 tests/test_vendor_antislop.py`. Nothing is downloaded at run time. The copy's text is not edited.
