# Proposal

## Why

The change delivery-ci-green (PR #5, merged 2026-11-14) rewrote step 3 of the One-time setup in `docs/release.md`: npm refuses a token that bypasses two-factor authentication for a direct publish, so the first version (v0.2.0) went to npm once by hand, and later versions publish through the trusted publisher. The requirement Registry publishing and the npm job of `.github/workflows/release.yml` still describe the secret `NPM_TOKEN` as the first-publish path, a branch that npm refuses and that `docs/release.md` tells the owner to leave unset.

## What Changes

- The npm job of `release.yml` reads no npm token: the `NPM_TOKEN` env entry, its comment and the `npm config set ... _authToken` line go; the job publishes only through the trusted publisher with provenance.
- The requirement Registry publishing says the npm job reads no token and that the first version is published once by hand by `docs/release.md`.

## Capabilities

### New Capabilities

### Modified Capabilities
- `registry-release`: the requirement Registry publishing drops the `NPM_TOKEN` branch.

## Impact

`.github/workflows/release.yml`, `solo-sdd/specs/registry-release/spec.md`, `tests/test_release.py`

## Out of Scope

- `docs/release.md`: step 3 already describes the manual first publish; its line to leave `NPM_TOKEN` unset stays true.
- The PyPI job and its trusted publishing.

## Depends On

none

## Source

"In solo-sdd, `docs/release.md` now says the first npm publish is done once by hand and the secret `NPM_TOKEN` stays unset. Two places still describe a token path for the first publish ... The change either drops the token branch or rewords its purpose, through a MODIFIED requirement." (the starting session, 2026-11-14)
