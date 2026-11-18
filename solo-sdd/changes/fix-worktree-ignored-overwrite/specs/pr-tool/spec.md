## ADDED Requirements

### Requirement: Ship keeps worktree ignored files
Before `sdd-pr.py ship` merges `origin/<main>` into WORKTREE, it SHALL compare the paths that merge writes (the diff from the merge base of WORKTREE's `HEAD` and `origin/<main>` to `origin/<main>`) with the files WORKTREE holds untracked; any match SHALL stop with code 1 and `not shipped: merge would overwrite ignored files in WORKTREE: <paths>`, WORKTREE on its previous commit, the files unchanged, no push and no PR.

#### Scenario: The base branch now tracks an ignored file
- **WHEN** WORKTREE holds an ignored `docs/notes.md`, and `origin/main` gained a commit that tracks `docs/notes.md`
- **THEN** `ship` ends with code 1 naming `docs/notes.md`, the file keeps its text, and nothing is pushed
