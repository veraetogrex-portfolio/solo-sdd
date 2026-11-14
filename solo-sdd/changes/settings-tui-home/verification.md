## Live Scenario

Every step runs with a temporary `HOME` (never the owner's home) holding `solo-sdd install --agents claude,codex`, with fake `claude` and `codex` executables on `PATH` so both are detected.

1. `HOME=$T solo-sdd install --hooks`, then `HOME=$T solo-sdd uninstall --hooks` → the hook entries, `statusLine`, the `autoMode` rule and the depth variable gone from `$T/.claude/settings.json`, a person's hook added before stays, `HOME=$T solo-sdd status` shows the same copies as before; a second `uninstall --hooks` writes nothing and says the hooks are not connected.
2. The stand `python3 tests/stands/settings-tui-home.py` runs `solo-sdd settings` through a pseudo-terminal in that `HOME`, at 120x40 and 40x12, with colours and with `NO_COLOR=1`:

| Element | Action | Expected result |
|---|---|---|
| Machine section | open | `claude`, `codex`, `other` ticked, hooks off, global rules off, source and version, copy counts, the `doctor` warn lines |
| Machine section in a folder without `solo-sdd/` | open | only this section |
| `codex` | untick, apply | the list names `solo-sdd install --agents claude,other` and `~/.codex`; after `y` the output is shown, `$T/.codex/skills` holds no unchanged copy |
| hooks | turn on, apply, `y` | `solo-sdd install --agents claude,other --hooks` ran, hooks on |
| hooks | turn off, apply, `y` | `solo-sdd uninstall --hooks` ran, hooks off |
| global rules | turn on, apply, `y` | the block is in `$T/AGENTS.md`, `$T/.codex/AGENTS.md` and `$T/.claude/CLAUDE.md` |
| `claude` with hooks on | untick, apply, `y` | the refusal naming `claude` is shown; `$T` has the same files and bytes as before |
| any edit | apply, then cancel | no command runs, `$T` unchanged |

## Needs

none

## Fallback

Not needed: everything runs in a temporary home.

## Result

<!-- Filled during apply: date, what was run, what was observed. -->

## Not Verified

- Independent acceptance of the last fix: review round 3 (the limit of `process.review-rounds`) found an Important introduced by round 2's edit, the Machine cursor not clamped after `r` or an apply when the doctor rows become fewer (an IndexError in the drawing). It is fixed (`read_machine` clamps `mpos`, test `Machine.test_fewer_doctor_rows_after_refresh`), but no reviewer has accepted the fix: reconsider the approach or a fourth round by the owner's decision. The change is not archived.

## Decisions Without Owner

- apply: `tests/test_cli.py` Hooks.test_unknown_flags used `uninstall --hooks` as its example of an unknown flag; the new requirement Uninstall hooks only makes it a command → the example becomes `uninstall --hooks --purge`, which the command does not know; the assertion (an unknown flag set exits 2) is kept
- analyze: the main requirement Settings screen refuses a folder without `solo-sdd/` with exit 1, while the Machine section opens outside a project → a MODIFIED Settings screen in this delta: only the Machine section, naming `solo-sdd init` — the two could not both hold
- analyze: `uninstall --hooks` on a broken `settings.json` was not described → `fail settings:` with no write and `_hooks` kept, as `install --hooks` refuses it — the record must survive until the file can be read
- analyze: when the `doctor` rows are computed was open (its checks call programs with a 30 s timeout) → once on opening the section and on a refresh key — a redraw must not wait on programs
