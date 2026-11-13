# quickstart-demo Specification

## Purpose
Gives a new user a small working solo-sdd project to run one full change cycle on before using solo-sdd on their own code.

## Requirements

### Requirement: Demo project
`examples/demo/` SHALL hold a runnable app with its own tests, a `solo-sdd/` tree with one main spec, one archived and one open change ready for `/spec-next`, and `WALKTHROUGH.md`. `solo-sdd validate --all` and the app's tests SHALL pass in it; `tests/test_demo.py` SHALL check both.

#### Scenario: The demo stays valid
- **WHEN** `python3 tests/test_demo.py` runs
- **THEN** both checks pass in a temporary copy of `examples/demo/`

### Requirement: Walkthrough runs as written
Every line of the fenced `bash` blocks of `WALKTHROUGH.md` SHALL run as written in a temporary `HOME`, in the order of the file, except the `git clone` line, which needs the network: the test puts the repository's own `examples/demo/` where that clone would put it. The open change SHALL be completable by `/spec-next` in the copy, and the quick start of `README.md` SHALL link `examples/demo/WALKTHROUGH.md`.

#### Scenario: Commands
- **WHEN** `tests/test_demo.py` runs the walkthrough's `bash` blocks in a temporary `HOME`
- **THEN** each command exits with code 0, and a failing one fails the test with its text

#### Scenario: The README link
- **WHEN** `tests/test_demo.py` reads the quick start section of `README.md`
- **THEN** it links `examples/demo/WALKTHROUGH.md`
