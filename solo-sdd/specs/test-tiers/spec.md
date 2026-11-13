# test-tiers Specification

## Purpose
solo-sdd's own suite is split into fast, slow and release sets, so a round of checks takes minutes and the release set runs only before a release.

## Requirements

### Requirement: Test marks
A test marked `slow` or `release` by `tests/marks.py` SHALL run only when `SOLO_SDD_TESTS` names its tier or a later one (`fast` < `slow` < `release`); an unmarked test SHALL always run. With no variable every test SHALL run, so a direct file run and a workflow that loops over the files keep the whole suite. An unknown value SHALL fail a file that imports `tests/marks.py`, naming the value.

#### Scenario: A release test in a round
- **WHEN** `SOLO_SDD_TESTS=slow` and a test is marked `release`
- **THEN** the test is skipped with the reason naming the tier

#### Scenario: A direct run
- **WHEN** `python3 tests/test_cli.py` runs without the variable
- **THEN** every test of the file runs, `test_wheel` included

#### Scenario: A typo in the tier
- **WHEN** `SOLO_SDD_TESTS=slwo` and `python3 tests/test_cli.py` runs
- **THEN** the file fails with a message naming `slwo` and the three tiers

### Requirement: Tiers in the runner
`tests/run.py --tier fast|slow|release` SHALL set `SOLO_SDD_TESTS` for every file it runs; without `--tier` the tier is `slow`, with `--affected` too. In the `fast` tier no marked test runs, and an unmarked test that runs longer than 2 s SHALL fail the run and be named with its seconds. After the summary line the runner SHALL print the line `skipped: <m>`.

#### Scenario: The fast tier
- **WHEN** the runner runs `--tier fast`
- **THEN** no test marked `slow` or `release` runs, and the line `skipped: <m>` after the summary counts them

#### Scenario: A slow unmarked test
- **WHEN** an unmarked test takes 3 s in the `fast` tier
- **THEN** the runner ends with code 1 and names that test and its seconds

#### Scenario: Affected files
- **WHEN** the runner runs `--affected solo_sdd/cli.py` without `--tier`
- **THEN** the `slow` tests of the files the map names for it run, and their `release` tests are skipped

#### Scenario: A file without unittest tests
- **WHEN** a test file has no unittest test case, as `tests/test_work_hooks.py` before `hooks-test-unittest`
- **THEN** it runs as a whole in every tier, its line shows its seconds, and the 2 s check does not fail it

### Requirement: Release set
The `release` tier SHALL hold `tests/test_sdd_eval.py`, `tests/test_publish_first.py`, `test_cli.EntryPoint.test_wheel` and `test_npm_package.Contents`; the `slow` tier the tests of 1 s or more measured on the owner's machine. The first value of the `Tests` row of `AGENTS.md` SHALL be the run before delivery (`--tier slow`); the row SHALL then name a round (`--tier fast`, then `--affected`) and the run before a release tag (`--tier release`).

#### Scenario: A round
- **WHEN** an agent runs the round commands of `AGENTS.md`
- **THEN** none of the `release` tests runs

#### Scenario: The command scripts read
- **WHEN** `sdd-eval.py` takes the first value of the `Tests` row and appends test file names
- **THEN** the command is the `--tier slow` run, and only the named files run
