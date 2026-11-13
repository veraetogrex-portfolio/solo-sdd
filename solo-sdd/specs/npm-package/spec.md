# npm-package Specification

## Purpose
solo-sdd installs through npm the same way as OpenSpec and gives the same `solo-sdd` command as the Python package.

## Requirements

### Requirement: npm wrapper
The npm package SHALL give the command `solo-sdd`, which runs the `solo_sdd` module the same way as `python -m solo_sdd`, with the same arguments, the same standard streams and the same exit code. The module SHALL be taken from the root of the installed package, which holds `solo_sdd/` and the data in the same layout as the repository, even if the current folder has another `solo_sdd/`; `PYTHONPATH` SHALL point to this root.

#### Scenario: Exit code
- **WHEN** `solo-sdd frobnicate` is run through the npm wrapper
- **THEN** exit code 2 and the same text as `python3 -m solo_sdd frobnicate`

#### Scenario: A foreign solo_sdd in the current folder
- **WHEN** `solo-sdd status` runs through the npm wrapper from a solo-sdd clone or another folder with its own `solo_sdd/`
- **THEN** the first output line names the root of the installed npm package as the source

#### Scenario: No Python
- **WHEN** `PATH` has neither `python3` nor `python`, and `SOLO_SDD_PYTHON` is not set
- **THEN** one line `solo-sdd: Python 3.9+ needed (found: none)`, exit code 1

#### Scenario: Choosing Python
- **WHEN** the wrapper looks for Python
- **THEN** the order is `SOLO_SDD_PYTHON`, `python3`, `python`; the first found with version 3.9 or newer is used

#### Scenario: Only an old Python
- **WHEN** all found Pythons are older than 3.9
- **THEN** the line `solo-sdd: Python 3.9+ needed (found: <versions>)`, exit code 1

### Requirement: Package contents and version
`npm pack` SHALL include `bin/`, `solo_sdd/`, `skills/`, `global/`, `schema/`, `templates/`, `targets.json`, `ALGORITHM.md`, `LICENSE`, `README.md` and SHALL NOT include `tests/`, `solo-sdd/`, `.github/`, `docs/` and files git ignores (`__pycache__/`, the owner's personal files from the working copy). The version in `package.json` SHALL match `version` in `pyproject.toml` and `solo_sdd.__version__`. `tests/test_npm_package.py` checks both conditions.

#### Scenario: The version diverged
- **WHEN** `package.json` has `0.1.1`, and `solo_sdd/__init__.py` has `0.1.0`
- **THEN** `python3 tests/test_npm_package.py` ends with code 1 and names both versions
