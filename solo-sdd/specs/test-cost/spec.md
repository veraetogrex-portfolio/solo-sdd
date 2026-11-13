# test-cost Specification

## Purpose
solo-sdd's own slow tests keep every check while their setup, examples and waits cost less.

## Requirements

### Requirement: Shared repository fixtures
A test class of the `tests/test_sdd_*.py` files or `tests/test_publish_first.py` with more than one test whose tests each build the same git fixture with more than one git command SHALL build it at most once per process through `tests/shared_repo.py` and give each test its own copy of the whole fixture folder (every repository, remote and worktree in it); no test SHALL see another test's changes, and no path inside a copy SHALL point into the template or another copy.

#### Scenario: Two tests of one class
- **WHEN** the first test of a class commits, adds an untracked file and pushes to the remote in its copy
- **THEN** the second test's copy has no such commit, file or pushed ref

#### Scenario: A fixture with a remote and a worktree
- **WHEN** the fixture holds a bare remote and a linked worktree
- **THEN** the copy's `origin` URL and its worktree's `gitdir` point inside the copy

#### Scenario: A fixture that cannot be copied
- **WHEN** a class's fixture holds a path outside its folder that `tests/shared_repo.py` cannot rewrite
- **THEN** that class keeps building its fixture per test, and verification.md names it

### Requirement: Example budgets
A property test of solo-sdd's suite, `tests/test_work_hooks.py` excepted, that starts a process or creates a repository per example SHALL state two example counts through `tests/marks.py`: its current count as the full one and a reduced one of at least 20 (or the full count when smaller). The `release` tier SHALL run the full count; the `fast` and `slow` tiers and a run with no `SOLO_SDD_TESTS` SHALL run the reduced one.

#### Scenario: A round
- **WHEN** `test_abandoned_claims_property` runs in the `slow` tier
- **THEN** it runs the reduced count, and in the `release` tier the full count of 120

#### Scenario: A direct run
- **WHEN** `python3 tests/test_sdd_dispatch_plan.py` runs with no `SOLO_SDD_TESTS`
- **THEN** its budgeted property tests run the reduced count

### Requirement: Short real timeouts
A test of a real timeout SHALL set the lowest value its setting accepts: at most 0.2 s for a module constant the test patches (`setup_detect.TIMEOUT`, `sdd_worktree.AFTER_LIMIT`), 1 s for a setting of whole seconds (`SDD_DISPATCH_TIMEOUT`, `sdd_eval.py --timeout`), whose parsing SHALL NOT change. A test that fails at that value in any of 5 runs on the owner's machine SHALL keep its previous value, named in verification.md.

#### Scenario: A patched constant
- **WHEN** `test_setup_detect` `test_gh_timeout` runs
- **THEN** `TIMEOUT` is at most 0.2 s and the protection is still `unknown`

#### Scenario: A whole-second setting
- **WHEN** `LandTest.test_command_timeouts_a_hanging_git_step_in_land_local` runs
- **THEN** `SDD_DISPATCH_TIMEOUT` is `1` and the test checks `timeout after 1 s`, unless 5 runs showed it fails at 1 s

### Requirement: No check lost
The change SHALL keep every test method and every assertion of the files it edits; only fixtures, example counts and timeout values change, and an asserted timeout text follows its new value.

#### Scenario: Counts before and after
- **WHEN** the stand counts, by Python's `ast`, the `test_` methods and the `assert` statements and `self.assert*` calls per edited file on the base commit and the branch
- **THEN** the counts are equal
