# Proposal

## Why

The first CI run of the public repository (2026-11-13, Ubuntu, Python 3.14) failed `tests/test_integration_run.py` `RecordReuse.test_record_reuse_an_edit_makes_a_new_record`: `(0, 2, 1) != (0, 2, 2)`, the edit made no new record. Reproduction: commit `README.md` (`readme\n`), rewrite it as `edited\n` (same size) in the same second, call `check`: the tree hash does not change, so the call reuses the old record. Cause: `tree_hash` in `solo_sdd/integration_run.py:86` copies the real index with `shutil.copyfile`, which gives the copy the current time. Git treats an entry as racily clean only when the file is not older than the index, so the newer copy makes git trust the matching stat and skip the content of the edited file.

## What Changes

- `tree_hash` copies the index with its timestamps (`shutil.copy2`), so git's racy-entry check sees the real index time and rereads such a file; the copy in `global/work_hooks.py` follows by `scripts/sync_blocks.py`.

## Capabilities

### New Capabilities

### Modified Capabilities
- `integration-run`: requirement Record reuse gets the scenario An edit in the second of the index write.

## Impact

- `solo_sdd/integration_run.py`
- `global/work_hooks.py`
- `tests/test_integration_run.py`
- `solo-sdd/specs/integration-run/spec.md`

## Out of Scope

- `tests/test_shared_repo.py` depends on the machine's default branch name: a separate `light:` fix.
- Other users of a copied index: none found besides the tree-hash block.

## Depends On

none

## Source

The first CI run of the public repository, 2026-11-13: "FAIL: test_record_reuse_an_edit_makes_a_new_record ... AssertionError: Tuples differ: (0, 2, 1) != (0, 2, 2)".
