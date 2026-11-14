## MODIFIED Requirements

### Requirement: Policy file is the user's
The comment of `global/model-policy.json` and `docs/hooks.md` SHALL say that the model lists and the `browser` key are edited in the deployed copy `~/.claude/hooks/model-policy.json`, that `install`, `update` and `sync.py push` keep an edited copy as `drift` instead of overwriting it, so a newer shipped model list is not taken while it is `drift`, and how to take it, as probed.

#### Scenario: An edited copy
- **WHEN** a user added a model to `cheap` in the deployed copy and runs `python3 sync.py push`
- **THEN** the copy stays as edited and `sync.py status` shows it as `drift`

### Requirement: Known bypasses of the merge guard
These direct merge forms SHALL pass `guard` as outside it, each pinned by a test that it passes: `xargs`, `find -exec`, `sudo -u`, `env -u`, a shell function, `bash -c`, `eval` or a quoted assignment after `A=(…)` or in `=(…)`, substitutions nested deeper than 3, a `)` in a pattern or quoted text that ends a substitution early, a quoted `(` that keeps one open, a backslash-newline between `$` and `(`. Branch protection is the boundary.

#### Scenario: A known bypass closed
- **WHEN** a change makes `guard` refuse one of these forms
- **THEN** the known-limit test fails until the form moves to the refused tests and `docs/hooks.md`

#### Scenario: A known false refusal
- **WHEN** a command with `$'`, `=(`, `${` or a `#` word has `(`, `;`, `|` or a newline before `gh pr merge` inside a message, as in `git commit -m "fix #42 (gh pr merge is refused)"` or `A=(x y); git commit -m "a; gh pr merge later"`
- **THEN** it is refused: in such a form quotes are ignored, and the test pins it

#### Scenario: An array assignment before a merge
- **WHEN** the agent runs `A=(1 2) gh pr merge 5`, `cat =(gh pr merge 5)`, `A=(1 2) \gh pr merge 5` or `cat =(/usr/bin/env gh pr merge 5)` in a project with a `solo-sdd/` tree
- **THEN** `guard` refuses it: a line with `=(` is read with quotes ignored, so the merge after it is found

#### Scenario: A quote inside a word after an array assignment
- **WHEN** the agent runs `A=(1 2) 'g'h pr merge 5` or `cat =(gh p''r merge 5)` in a project with a `solo-sdd/` tree
- **THEN** `guard` lets it through: a quote inside a word after `A=(…)` or in `=(…)` is a known bypass, pinned by a test that it passes
