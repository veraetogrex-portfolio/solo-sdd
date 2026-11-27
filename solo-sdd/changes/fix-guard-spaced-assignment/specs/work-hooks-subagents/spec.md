## MODIFIED Requirements

### Requirement: Direct merge refused in a process tree
`guard` SHALL refuse a Bash command that runs `gh pr merge` or a `gh api` call to `pulls/<n>/merge` when the git working copy of the hook's `cwd` has a `solo-sdd/` tree, naming `sdd-pr.py merge`, whose gates a direct merge skips; outside such a tree it passes. A quoted argument, a heredoc body read by a text program and a search pattern are not commands. The check guards against an agent's accidental direct merge by the plain forms; it is not a security boundary.

#### Scenario: A process tree
- **WHEN** the project has `solo-sdd/` and the agent runs `gh pr merge 5 --squash`
- **THEN** the command is refused, the reason names `sdd-pr.py merge`; in a repository without `solo-sdd/` the same commands pass

#### Scenario: The API form
- **WHEN** the project has `solo-sdd/` and the agent runs `gh api -X PUT repos/o/r/pulls/5/merge`
- **THEN** the command is refused

#### Scenario: No tree
- **WHEN** the repository has no `solo-sdd/` and the agent runs `gh pr merge 5 --squash`
- **THEN** the command passes

#### Scenario: Text about a merge
- **WHEN** the agent runs `git commit -m "explain gh pr merge"` in a project with `solo-sdd/`
- **THEN** the command passes: a message is not a command

#### Scenario: An assignment with a spaced substitution
- **WHEN** the project has `solo-sdd/` and the agent runs `TS=$(date +%s) gh pr merge 5 --squash`, `TS=$(date +%s) sudo gh pr merge 5` or `TS=$(date +%s) gh api -X PUT repos/o/r/pulls/5/merge`
- **THEN** the command is refused, the reason names `sdd-pr.py merge`; in a repository without `solo-sdd/` the same commands pass
