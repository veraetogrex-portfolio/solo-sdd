## MODIFIED Requirements

### Requirement: Worktree venv link
For `.venv` at the root of `MAIN` `sdd-worktree.py setup` SHALL create a symbolic link to it in `WORKTREE` if there is none, and add to `info/exclude` of the shared git directory the patterns `node_modules` and `/.venv` (each other link at its path from the root) without a trailing slash if they are not there, so the links do not get into `git status` and commits; a setup that fails after a link is made SHALL still add the pattern of that link.

#### Scenario: The .venv link is invisible to git
- **WHEN** `MAIN` has `.venv`, and `info/exclude` has no `.venv` pattern
- **THEN** `WORKTREE` has the `.venv` link, `info/exclude` has the line `/.venv`, `git -C <WORKTREE> status --short` does not show it

#### Scenario: A later link fails
- **WHEN** `setup` made the `node_modules` link and then failed on the `.venv` link
- **THEN** `setup` ends with code 1, `info/exclude` has the line `node_modules`, `git -C <WORKTREE> status --short` does not show the link, and `remove` is not refused for it
