## ADDED Requirements

### Requirement: Overwrite check command
`sdd-pr.py overwrites <WORKTREE> <ref>` SHALL compare, by the same rule as Ship keeps worktree ignored files, the paths merging `<ref>` into WORKTREE writes with the files WORKTREE holds untracked, and change nothing: no match SHALL print nothing with code 0; a match SHALL print `merge would overwrite ignored files in WORKTREE: <paths>` with code 1; a failed git step SHALL print `<step>: <reason>` with code 1, never code 0.

#### Scenario: A branch with its own commit
- **WHEN** WORKTREE's branch has a commit of its own, WORKTREE holds an ignored `solo-sdd/config`, and `<ref>` tracks `solo-sdd/config`
- **THEN** the command ends with code 1 naming `solo-sdd/config`, and the file, the index and `HEAD` are unchanged

#### Scenario: An unknown ref
- **WHEN** `<ref>` names no commit
- **THEN** the command ends with code 1 and the failed step, not code 0
