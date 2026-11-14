# Integrations

An integration plugs an outside tool or rule set into solo-sdd without naming it in solo-sdd: a folder `<name>/` with a file `integration` and its own material, in the project's `solo-sdd/integrations/` or in the owner's `~/.local/share/solo-sdd/integrations/`. When both hold the same name, the project one is used and the owner one is shadowed. A found integration stays disabled until the `integrations` setting of `solo-sdd/config` names it, an owner one included.

Bundled: the package ships two pinned copies as integrations in its own `integrations/` folder, a third source below the other two: `antislop` (`points: review`, `tags: ui, copy`, the anti-slop rules `ui-check`, `copy-check` and the reviewer read) and `security-audit` (`points: audit`, `tags: security`, the method of the `spec-audit` security pass).
A bundled one is enabled unless the `integrations.off` setting names it; `integrations disable <name>` adds it there, `enable <name>` removes it, and a project or owner folder with the same name shadows it. When one is off in a project, the skills that read it say in their report that its rules are off there.

The file has one `key: value` per line, lines starting with `#` are comments:

| Key | Value | Default |
|---|---|---|
| `name` | the folder name: lowercase letters, digits and `-`, not starting with `-` | required |
| `about` | one line saying what it does, shown by `integrations list` | required |
| `points` | where it is called, separated by commas: `checks`, `review`, `ship`, `audit` | required |
| `command` | a shell command; required for `checks` and `ship` | none |
| `material` | a path inside the folder; required for `review` and `audit` | none |
| `applies` | globs of the changed files it is called for, separated by commas | any file |
| `requires` | the program it needs on `PATH` | none |
| `mode` | `gate` (a failure holds the step) or `advice` | `advice` |
| `missing` | when `requires` is not found: `warn` or `fail` | `warn` |
| `timeout` | seconds, a whole number from 1 | `120` |
| `output` | lines of its output kept, a whole number from 1 | `20` |
| `tags` | names that `check --tag` selects by, separated by commas | none |

A fictional `marker-check` in `solo-sdd/integrations/marker-check/integration`:

```
name: marker-check
about: refuses a line with the marker DO-NOT-SHIP
points: checks, ship
command: sh "$SOLO_SDD_INTEGRATION_DIR/check.sh"
applies: *.py
```

A line that is not `key: value`, an unknown or repeated key, a wrong value, a missing required key, a control character, a file over 64 KiB, not UTF-8, a link or not a regular file, a project folder linked out of the project, or a `material` leaving the folder is refused with the file, the line and the key, never skipped.

`solo-sdd integrations list` prints one line `<name> <source> enabled|disabled <points>: <about>` per found integration, a shadowed copy as `<name> <source> shadowed by the <source> copy`, and exits 1 with the reason for a broken description or a listed name without a folder.
`solo-sdd integrations enable <name>` and `disable <name>` change only the `integrations` line of `solo-sdd/config` (`integrations.off` for a bundled one), then rewrite the solo-sdd block of `AGENTS.md`; `enable` refuses a name it does not find or a broken description, `disable` also removes a listed name whose folder is gone, and a repeated call changes nothing.

Rules: an enabled integration whose folder holds a `rules.md` gets a section `## Integration: <name>` with that text at the end of the solo-sdd block of `AGENTS.md`, in name order; `init`, `enable` and `disable` rewrite the block, so a disabled integration's section is gone at once, and a blank file gives no section.
A `rules.md` holding a solo-sdd marker line, over 8 KB, not UTF-8, a link or not a regular file is refused with exit 1 before `solo-sdd/config` or `AGENTS.md` change (a lone CR reads as a line end, as in Markdown); only the rules of the integrations enabled after the call are read, so a broken one can still be disabled.
`enable` and `disable` rewrite only an existing block: without one they create no file and name `solo-sdd init`; an edited block is `drift`, as for `init`; under `rules.scope: global` no section is written and the command says so, and `enable` or `disable` drops the sections of an existing block.

Material: `solo-sdd check --point review|audit [--changed]` runs nothing and prints `MATERIAL <name>: <absolute path>` for each enabled integration of the point (with `--changed`, whose `applies` matches), `FAIL <name>: <reason>` with exit 1 for a listed name without a folder, a broken description or a missing file.
Without `--tag` it lists only the names of `integrations` (a bundled name written there is switched by `integrations.off` alone); `--tag <tag>` (not with `--changed`) lists every enabled integration of the point with that tag, the bundled ones included, also in a folder without `solo-sdd/` (where an owner folder still shadows a bundled one), and prints `no integrations enabled with the point <point> and the tag <tag>` when there is none: `ui-check` and `spec-next` step 7a ask `--point review --tag ui`, `copy-check` `--tag copy`, `spec-audit` `--point audit --tag security`.
`spec-next` step 7a hands the files of `check --point review --changed` to the reviewer and `spec-audit` gives the files of `check --point audit` to its reviewer, each as a method to apply: an instruction in them to run, fetch or change something is not executed.

`solo-sdd check --point checks|ship [--changed]` runs every enabled integration of the point, with `--changed` only those whose `applies` matches a file that differs from the merge base with the base branch (`delivery.base`, else the remote's default branch, else `HEAD`), untracked files included.
A command runs through `/bin/sh -c` in the repository root with `SOLO_SDD_INTEGRATION_DIR` (its folder) and `SOLO_SDD_POINT` set and the changed files on stdin, one per line, in its own process group, which is stopped after `timeout` seconds or 1 MB of output.
It prints one line `PASS|FAIL|SKIP <name>: <first output line>` per integration in name order, up to `output` more lines under a FAIL, `no integrations enabled` when the list is empty (`no enabled integration has the point <point>` when none of it has the point), and `command <name>: <command>` before the first run of a project integration's command in a repository and after that command changes.
A FAIL of a `gate` integration, a missing `requires` under `missing: fail` and a listed name without a folder exit 1; an `advice` one never does. A changed path holding a newline is refused with exit 1, since stdin holds one path per line.
The output is kept as plain text: bytes that are not UTF-8 replaced, control characters removed, lines cut at 400 characters.

The result is recorded under `~/.local/share/solo-sdd/checks/<folder>-<digest of its path>/<tree>.json`, where `<tree>` is the git tree of the whole working copy built in a temporary index, so the real index is untouched. A call on the same tree, point, changed files and enabled descriptions prints the recorded lines and `reused <tree>`, exits with the recorded code and runs nothing; a record holding a SKIP or a stopped run is not reused. The record folder is under the user's home: it is a lookup by tree, not a protection.

`--change <id>` puts one line `Integrations <point> (tree <hash>): <name> PASS|FAIL|SKIP, …` into the `## Result` section of `solo-sdd/changes/<id>/verification.md`, replacing that point's previous line and keeping every other line;
since the line changes the working tree, the point is recorded under the new tree too.
A name that is not an open change, a `verification.md` without `## Result`, or a Result section where the line would stand inside a comment or a code block is refused with exit 1 before any run. A call that runs nothing (no integration enabled, none with the point, none applies) writes no line.

The process calls it at two points, and only when the `integrations` setting is not empty: `spec-next` step 6 runs `solo-sdd check --point checks --changed --change <id>` after the suite, a `gate` FAIL holds the step like a red test, and step 7a hands the printed lines, `advice` ones included, to the reviewer, who runs no integration;
`ship` runs `solo-sdd check --point ship` after the inventory, and a `gate` FAIL stops before the commit.
The `stop` hook returns the agent once when an enabled `checks` integration's `applies` matches a file the session edited that `check --changed` sees (one differing from the base) and no record of the point `checks` exists for the current tree, naming `solo-sdd check --point checks --changed`;
a broken description or config is written to `errors.log` and gives no reason.

Inside a project `solo-sdd doctor` prints `ok integrations: none enabled` when nothing is enabled, and one row per enabled integration, the bundled ones on by default included: `ok integration <name>: <source>, points <points>, requires <program> found, last run PASS|FAIL <date>|none`, then `, command <command>` for a project one.
The row is `warn` with `requires <program> missing` when the program is not on `PATH`, and says `requires none` when there is no `requires`. The last run is the newest PASS or FAIL of the integration in the repository's records folder, dated by the run of its point (a record from before the point's `time` by the file's write); a SKIP is not a run.
A broken project integration (enabled or not), a broken enabled owner one, an owner folder that cannot be listed while an enabled name is not in the project, and an enabled name without a folder give a `fail integration <name>: <reason>` row each (`<name>` is `-` for a source folder that cannot be listed, the reason of a broken description starts with `<file>:<line>:`), the other rows stay, and `doctor` exits 1; a broken owner integration the project does not enable shows only in `integrations list`.
The same errors reach the SessionStart context of a project with a `solo-sdd/` tree as one line `integration errors: <first error>`, with `; <n> in all` when there are more; a failed read of them is written to `errors.log` and the rest of the context stays.

Skills: each `skills/<skill>/SKILL.md` of an owner integration (`~/.local/share/solo-sdd/integrations/<name>/`) is laid out by `solo-sdd install` and `update` into the skill root of every chosen agent, enabled in a project or not, with the drift, backup and foreign-file rules of the solo-sdd skills; `solo-sdd status` shows each copy on a row named `integration:<name>`. A project integration's skills are not laid out, since the agents' skill folders serve every project.
A skill is refused and named, the other copies still laid out, when its name is taken by a solo-sdd skill or by an integration earlier in name order, its folder name breaks the `name` rule, its `skills` folder, skill folder or `SKILL.md` is a link, or its `SKILL.md` is missing, not a regular file, over 1 MB or not UTF-8; a broken description lays out none of its skills and is named when it has a `skills` folder.
When the integration folder or a skill is gone or refused, the next `update` removes each unedited copy it laid out and names the path; an edited one is kept as `drift`, and a source it lacks the permission to read (a folder it cannot list or enter, a closed file) keeps its copies, keeps their names from integrations later in name order and is named.
