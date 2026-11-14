# registry-release Specification

## Purpose
Builds one set of release files from the files git tracks, proves them before upload and publishes the same files to PyPI and npm from a tag, so a user installs solo-sdd by its name from either registry.

## Requirements

### Requirement: Release versions
`python3 scripts/release_check.py <tag>` SHALL exit 1 before building and name the tag and each version when the tag is not `v` followed by the version of both `package.json` and `solo_sdd/__init__.py`. It SHALL also exit 1 before building and name the version when `CHANGELOG.md` has no section `## <version>`. After building it SHALL also exit 1 when a built file name carries another version.

#### Scenario: Tag and version differ
- **WHEN** the tag is `v0.2.1` and `package.json` and `solo_sdd/__init__.py` hold `0.2.0`
- **THEN** exit code 1, the output names `v0.2.1` and `0.2.0`, nothing is built

#### Scenario: A version without a changelog section
- **WHEN** the tag and both versions are `0.3.0` and `CHANGELOG.md` has no `## 0.3.0`
- **THEN** exit code 1, the line starts with `fail changelog` and names `0.3.0`, nothing is built

### Requirement: Release contents
The release check SHALL build into `dist/` the sdist, the wheel from that sdist and the npm tarball, and print one line per file with its name and size. It SHALL exit 1 before building and name each tracked file with uncommitted edits. It SHALL exit 1 and name each path and its package when a package holds a file `git ls-files` does not list, the sdist one under `solo-sdd/`, or the wheel or npm tarball one under `tests/`, `solo-sdd/`, `docs/`, `.github/`, `examples/` or `scripts/`.

#### Scenario: Ignored files on disk
- **WHEN** the working copy has the git-ignored `global/claude-gui.py` and `global/claude-safe.py`
- **THEN** the release check passes and none of the built files contains them

#### Scenario: A skill kept out of git locally
- **WHEN** `skills/my-skill/SKILL.md` lies on disk and only the clone's own `info/exclude` keeps it out of git
- **THEN** exit code 1 and the line names `skills/my-skill/SKILL.md` and `npm`

#### Scenario: The development log
- **WHEN** the tracked `solo-sdd/changes/archive/` holds local paths and session ids
- **THEN** the sdist has no file under `solo-sdd/` and still has `tests/`

#### Scenario: An uncommitted edit
- **WHEN** a tracked skill file has an edit that is not committed
- **THEN** exit code 1, the line names the file, nothing is built

#### Scenario: A packed file outside git
- **WHEN** a package file list holds a path that `git ls-files` does not list
- **THEN** exit code 1 and the line names that path and the package

### Requirement: Release smoke
The release check SHALL install the wheel into a new venv and the npm tarball into a new npm prefix, and SHALL exit 1 unless `solo-sdd --version` from each prints the version.

#### Scenario: Clean release
- **WHEN** the tag matches the versions and the tree is the committed one
- **THEN** exit code 0, `dist/` holds `solo_sdd-<v>.tar.gz`, `solo_sdd-<v>-py3-none-any.whl` and `solo-sdd-<v>.tgz`, and both `--version` runs print `<v>`

### Requirement: Release workflow
`.github/workflows/release.yml` SHALL run on a pushed tag `v*`, fail when the repository is private or the tag commit is not on `main`, run the tests and the release check with that tag and hand the `dist/` files to the publishing jobs, which SHALL NOT build again. A GitHub release for the tag SHALL be created with the three files after both registries have the version. Only the two publishing jobs SHALL get `id-token: write`.

#### Scenario: A tag that does not match
- **WHEN** a tag `v0.3.0` is pushed while the versions are `0.2.0`
- **THEN** the check job fails and no publishing job runs

#### Scenario: A private repository
- **WHEN** the tag is pushed while the repository is private
- **THEN** the check job fails with a line that names the repository and `docs/release.md`

#### Scenario: A tag off main
- **WHEN** the tag points to a commit of a branch that is not merged into `main`
- **THEN** the check job fails with a line naming the tag and the commit

### Requirement: Registry publishing
The PyPI job SHALL use trusted publishing in the environment `pypi`. The npm job SHALL use trusted publishing with provenance in the environment `npm`, with npm 11.5.1 or newer, and SHALL read no npm token: the first version is published once by hand by `docs/release.md`. Each job SHALL skip what its registry already has: npm the version, PyPI each file already uploaded.

#### Scenario: A repeated run
- **WHEN** the workflow runs again for a tag both registries already have
- **THEN** both publishing jobs end with code 0 and say the version is already published

#### Scenario: No token in the npm job
- **WHEN** the Publish step of the npm job runs with a secret `NPM_TOKEN` set in its environment
- **THEN** it writes no `_authToken` to the npm config and runs only `npm view` and `npm publish ... --provenance`

### Requirement: Registry install documented
`README.md` SHALL install by the registry name in the quick start (`pip install solo-sdd`) and list `pip`, `uv tool`, `pipx` and `npm i -g solo-sdd` in the installation section, with the git address for the unreleased `main`. Every link to a repository file SHALL be an absolute `https://github.com/veraetogrex-portfolio/solo-sdd/blob/main/` address. `docs/release.md` SHALL hold the registry setup and the release steps.

#### Scenario: Links on a registry page
- **WHEN** `tests/test_readme.py` reads `README.md`
- **THEN** no link target is a relative file path; links to a heading of the same file (`#...`) are allowed

### Requirement: Release text
`python3 scripts/release_check.py --notes <tag>` SHALL print the lines of the `CHANGELOG.md` section of the tag's version without its heading, or exit 1 naming the version when there is no such section. The check job of `release.yml` SHALL hand that text to the job `github-release`, which SHALL create the release with it instead of generated notes.

#### Scenario: The release text
- **WHEN** `python3 scripts/release_check.py --notes v0.2.0` runs on a tree whose `CHANGELOG.md` has `## 0.2.0` with `- registry-release`
- **THEN** exit code 0, the output holds `- registry-release` and no `## ` line; with `v0.3.0` exit code 1 and the output names `0.3.0`

### Requirement: Workflow permissions
Every action in `.github/workflows/*.yml` SHALL be pinned by a full commit hash. Every workflow file SHALL set `contents: read` at its top, and only the job `github-release` of `release.yml` SHALL get `contents: write`.

#### Scenario: Write access only for the release
- **WHEN** `tests/test_release.py` reads every file `.github/workflows/*.yml`
- **THEN** each sets `contents: read` at its top, and `contents: write` stands only in the job `github-release` of `release.yml`

### Requirement: Changelog
`CHANGELOG.md` SHALL have a section `## <version>` for the version in `solo_sdd/__init__.py`, listing as `- <change>` the changes that version archived. When the tree has `solo-sdd/changes/archive/`, every listed change SHALL have a folder `solo-sdd/changes/archive/<date>-<change>`. A test in `tests/test_release.py` SHALL fail naming the version or the change when either does not hold. Equal package versions stay with the `npm-package` requirement Package contents and version.

#### Scenario: A version bump without a section
- **WHEN** `solo_sdd/__init__.py` says `0.3.0` and `CHANGELOG.md` has no `## 0.3.0`
- **THEN** the test fails naming `0.3.0`

#### Scenario: A change that was not archived
- **WHEN** the `## 0.2.0` section lists `- no-such-change` and the archive has no folder for it
- **THEN** the test fails naming `no-such-change`

#### Scenario: The public tree
- **WHEN** the test runs on a tree without `solo-sdd/` and the section of the current version exists
- **THEN** the test passes without reading the archive

#### Scenario: A fresh clone without the archive
- **WHEN** the test runs on a fresh clone that has `solo-sdd/specs/` but no `solo-sdd/changes/archive/`, as in CI, and the section of the current version exists
- **THEN** the test passes without reading the archive
