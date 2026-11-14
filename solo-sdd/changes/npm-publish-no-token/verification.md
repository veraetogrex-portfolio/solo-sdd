## Live Scenario

1. `python3 tests/test_release.py` → OK; `test_npm_job` asserts the npm job holds neither `NPM_TOKEN` nor `_authToken`, and fails on the tree before the change.
2. Stand: extract the `run:` script of the Publish step of the npm job from `.github/workflows/release.yml`, run it with `bash` under `GITHUB_REF_NAME=v9.9.9`, `NPM_TOKEN=fake` and a fake `npm` first on `PATH` that logs its arguments and fails `npm view` → the log holds `view solo-sdd@9.9.9 version` and `publish ./dist/solo-sdd-9.9.9.tgz --provenance --access public`, and no `config set` line. The same stand on the base commit logs `config set //registry.npmjs.org/:_authToken fake`.
3. CI `test` workflow on the PR → green.

## Needs

A real tag run of `release.yml` publishes to PyPI and npm: a prod action of the owner, not run here.

## Fallback

Step 2 runs the exact Publish script of the workflow with a fake `npm`; the next real tag run proves the trusted publisher path.

## Result

<!-- Filled during apply: date, what was run, what was observed. -->

## Not Verified

<!-- Filled during apply: what stayed unproven and why. Write: nothing - if all proven. -->

## Decisions Without Owner

<!-- Filled during apply: choices made without asking, and new changes created for out-of-scope work. -->
