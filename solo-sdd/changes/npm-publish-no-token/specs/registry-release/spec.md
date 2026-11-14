## MODIFIED Requirements

### Requirement: Registry publishing
The PyPI job SHALL use trusted publishing in the environment `pypi`. The npm job SHALL use trusted publishing with provenance in the environment `npm`, with npm 11.5.1 or newer, and SHALL read no npm token: the first version is published once by hand by `docs/release.md`. Each job SHALL skip what its registry already has: npm the version, PyPI each file already uploaded.

#### Scenario: A repeated run
- **WHEN** the workflow runs again for a tag both registries already have
- **THEN** both publishing jobs end with code 0 and say the version is already published

#### Scenario: No token in the npm job
- **WHEN** the Publish step of the npm job runs with a secret `NPM_TOKEN` set in its environment
- **THEN** it writes no `_authToken` to the npm config and runs only `npm view` and `npm publish ... --provenance`
