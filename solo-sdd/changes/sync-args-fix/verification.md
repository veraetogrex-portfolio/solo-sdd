## Live Scenario

Every step runs on a new empty temporary home (`H=$(mktemp -d)`), never on the real one; `find "$H" -type f | wc -l` counts what was written.

1. On the current code, `HOME=$H python3 sync.py push --help < /dev/null` → `all laid out`, exit 0, about 160 files in `$H`: the bug.
2. After the fix, the same command → the usage, exit 0, 0 files in `$H`.
3. `HOME=$H python3 sync.py push -h`, `status -h`, `pull ship --help` and `push --bogus --help` → the usage, exit 0, 0 files.
4. `HOME=$H python3 sync.py push --frobnicate`, `push --forc`, `status --bogus`, `push --quiet extra` → `unknown argument <arg>` first, the usage, exit 2, 0 files.
5. `HOME=$H python3 sync.py push`, then edit `$H/.claude/skills/ship/SKILL.md`, then `HOME=$H python3 -m solo_sdd sync pull ship --bogus` from the repository → exit 2, `git status` of the repository shows no change in `skills/ship/SKILL.md`.
6. `HOME=$H python3 sync.py push --quiet` → exit 0 and the copies laid out: known options still work.

## Needs

none

## Fallback

none needed

## Result

<!-- Filled during apply: date, what was run, what was observed. -->

## Not Verified

<!-- Filled during apply: what stayed unproven and why. Write: nothing - if all proven. -->

## Decisions Without Owner

- plan: the brief asked for exit 1 on an unknown option → exit 2 — `sync.py` without a command, `pull` without a name, `--from` without a value and every `solo-sdd` usage error already exit 2, and exit 1 there means a failed run (`fail state:`, `foreign`).
- analyze: `push --bogus --help` matched both the help and the refusal → help wins, exit 0, nothing written — both write nothing, and help on any argument line is what `argparse` does.
- analyze: `sync pull <name> --bogus` on a broken `state.json` matched Unknown arguments refused and Broken state refused → the argument refusal first (exit 2), recorded as a MODIFIED Broken state refused — the arguments are checked before the state is read.
- analyze: `solo-sdd sync pull --help` prints the `sync.py` usage of `solo_sdd/layout.py` → kept, no second usage text — the commands and options are the same.
