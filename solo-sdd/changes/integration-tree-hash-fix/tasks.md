## 1. Fix

- [ ] 1.1 Test `test_record_reuse_an_edit_in_the_second_of_the_index_write` (Requirement Record reuse): `core.checkStat minimal`, `core.trustctime false`, `README.md` rewritten with the same size, its mtime and the real index's mtime set to the second of the index entry; the next `check` writes a second record. It fails on the current code
- [ ] 1.2 `tree_hash` copies the index with `shutil.copy2`; `python3 scripts/sync_blocks.py` updates `global/work_hooks.py`; the test of 1.1 and `python3 scripts/sync_blocks.py --check` pass

## 2. Acceptance

- [ ] 2.1 Run the Live Scenario (or its Fallback) from verification.md and record the Result, Not Verified and Decisions Without Owner sections
- [ ] 2.2 Run `solo-sdd validate integration-tree-hash-fix` and archive the change with `solo-sdd archive integration-tree-hash-fix --yes`
