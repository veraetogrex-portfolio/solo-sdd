## MODIFIED Requirements

### Requirement: Plan committed
After gate G1 `spec-plan` SHALL commit the folders of the changes it created and changed in one commit `change: <id>, …`, naming in the commit only these folders. Under `delivery.mode` `pr` the commit SHALL go on a new branch `plan/<first id>` made in a temporary worktree and SHALL reach the main branch only through `ship`; the checked-out branch of the working folder SHALL NOT move. If `solo-sdd/changes` is ignored by git, there is no commit and the report has "plan outside git".

#### Scenario: The plan is committed
- **WHEN** `spec-plan` created changes `a` and `b`, and the tree has someone else's edit `src/x.py`
- **THEN** the last commit holds only `solo-sdd/changes/a/` and `solo-sdd/changes/b/`, the edit `src/x.py` stayed uncommitted

#### Scenario: Specs are ignored
- **WHEN** `git check-ignore solo-sdd/changes` finds a rule
- **THEN** there is no commit, the report has the line "plan outside git"

#### Scenario: A project that delivers through PRs
- **WHEN** `solo-sdd config get delivery.mode` prints `pr` and `spec-plan` created change `a` while `main` is checked out
- **THEN** `main` keeps its commit, the plan commit lies on `plan/a`, `ship` opens its PR with `sdd-pr.py open`, the report line `Plan:` names `plan/a` and the PR link, and after the merge the temporary worktree is removed and the local `main` is pulled

#### Scenario: A project that pushes the main branch
- **WHEN** `solo-sdd config get delivery.mode` prints `local`
- **THEN** the plan commit lies on the main branch and `ship` pushes it
