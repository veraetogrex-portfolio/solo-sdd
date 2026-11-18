## ADDED Requirements

### Requirement: Rebase keeps worktree ignored files
Under `delivery.local-merge: rebase`, before `reset --keep` moves WORKTREE to the rebased commit, `land-local` SHALL compare the paths that move writes (the diff between WORKTREE's `HEAD` and the rebased commit) with the files WORKTREE holds untracked; any match SHALL give code 1 with `not merged: rebase would overwrite ignored files in WORKTREE: <paths>`, the main branch, `change/<id>` and WORKTREE on their previous commits, the files unchanged.

#### Scenario: An ignored config the main branch now tracks
- **WHEN** WORKTREE holds an ignored `solo-sdd/config`, and the main branch moved ahead with a commit that tracks `solo-sdd/config`
- **THEN** code 1 names `solo-sdd/config`, the main branch, `change/b` and WORKTREE are on their previous commits, and WORKTREE's file keeps its text

#### Scenario: No ignored file in the way
- **WHEN** the rebased commit writes no path WORKTREE holds as ignored
- **THEN** the rebase lands as before, code 0
