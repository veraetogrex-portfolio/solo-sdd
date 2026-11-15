# Proposal

## Why

On 2026-11-15 `python3 sync.py push --help` ran a real deployment into `~/.claude`, `~/.codex` and `~/AGENTS.md` and laid out the global rules from a branch not yet merged. Reproduction (2026-11-15, temporary `HOME`): `HOME=<tmp> python3 sync.py push --help` → expected the usage and no file written → got `all laid out`, exit 0 and 162 files in the home; `push --frobnicate` gives the same. `solo-sdd sync pull <name> --bogus` pulls as if the flag were absent.

Cause: `_main` in `solo_sdd/layout.py:792` reads each option as a membership test (`"--force" in rest`, `solo_sdd/layout.py:798` and `:800`) and drops every other argument starting with `--` from the pull names (`solo_sdd/layout.py:803`), so an unknown argument never reaches a refusal. `sync.py` and `solo-sdd sync pull` both call this function. The other `solo-sdd` commands match their arguments exactly: a probe of `init`, `new`, `archive`, `config set`, `integrations enable`, `validate`, `list`, `migrate-agents` and `settings` with `--help` or `--bogus` gave exit 2 and wrote no file.

## What Changes

- `sync.py status`, `push` and `pull` (and `solo-sdd sync pull`) refuse an argument outside their own options with `unknown argument <arg>`, the usage and exit 2, before the state is read or a file is written.
- `--help` or `-h`, alone or anywhere after one of these commands, prints the usage, exits 0 and writes nothing, also next to an unknown argument.
- The refusal comes before the broken-state check, so `sync pull <name> --bogus` on a broken `state.json` exits 2, not 1.

## Capabilities

### New Capabilities

### Modified Capabilities
- `sync-layout`: new requirement Unknown arguments refused; Broken state refused yields to it.

## Impact

- `solo_sdd/layout.py`
- `tests/test_sync.py`

## Out of Scope

- Argument parsing of the other `solo-sdd` commands: already exact, probed above.
- Moving `layout._main` to `argparse`: a rewrite, not the removal of the cause.
- `sync.py` without a command or with an unknown command keeps printing the usage with exit 2.
- A repeated known option (`push --force --force`) stays accepted.

## Depends On

none

## Source

The session that started this work, 2026-11-15: "`python3 sync.py push --help` ignores the unknown `--help` flag and runs a real deployment into the agent folders (`~/.claude`, `~/.codex`, `~/AGENTS.md`); that happened on 2026-11-15 and laid out the global rules from a branch not yet merged."
