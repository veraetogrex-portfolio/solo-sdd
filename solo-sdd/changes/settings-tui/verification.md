## Live Scenario

The stand `python3 tests/stands/settings-tui.py` runs `solo-sdd settings` in a temporary git repository after `solo-sdd init --yes`, through a pseudo-terminal, sends the keys and reads the screen and the file. Run at terminal sizes 120x40 and 40x12, each with colours and with `NO_COLOR=1`.

| Element | Action | Expected result |
|---|---|---|
| key list | open the screen | groups and every registered key with value and source; the bottom shows the description of the first key |
| key list | Down and Up arrows | the selection moves and the bottom shows the selected key's description, default and team default |
| `delivery.mode` | Enter, pick `pr`, Enter | the key shows `pr` marked unsaved |
| `dispatch.limit` | Enter, type `0`, Enter | the reason "takes a whole number from 1" is shown, the value stays `2` |
| `dispatch.limit` | Enter, type `3`, Enter | `3` marked unsaved |
| `agents` | Enter, Space on `codex`, Enter | `claude, other` marked unsaved |
| `process.review-rounds` set to 4 in the file before opening | reset key | `3` with source `default`, marked unsaved |
| save key | press it | the list of edited keys with old and new values and a confirmation |
| confirmation | `y` | `solo-sdd/config` differs from before only in the edited lines; `solo-sdd config list` shows the new values with source `file` |
| quit | `q` with an unsaved edit | the question save, discard or back |
| quit | Ctrl-C | the process exits, no file write, the terminal echoes typed input again |
| save | after another process appended a comment to the file | nothing written, the message names the change on disk |
| broken file | open with line 4 `delivery.mode pr` | `solo-sdd/config:4` and the reason; Enter edits nothing |
| terminal 30 columns | open, then resize to 80 | the request to enlarge, then the key list |
| value with an ESC character in a comment | open | `\x1b` is shown, the terminal colours do not change |

Also: `solo-sdd settings < /dev/null; echo $?` and the same through the pseudo-terminal with `TERM=dumb` print a line naming `solo-sdd config` and `1`; in a folder without `solo-sdd/` on a terminal a line naming `solo-sdd init` and exit 1.

## Needs

none

## Fallback

Not needed: the stand runs locally through a pseudo-terminal. A person repeats rows 1-9 once by hand in Terminal.app at its default size.

## Result

<!-- Filled during apply: date, what was run, what was observed. -->

## Not Verified

<!-- Filled during apply: what stayed unproven and why. Write: nothing - if all proven. -->

## Decisions Without Owner

- analyze: the UI rule asks for widths 1280 and 390 and every theme, written for web pages → terminal sizes 120x40 and 40x12 (the smallest the screen supports) and colours with and without `NO_COLOR` — the screen is a terminal, it has no pixel width and no theme of its own
- analyze: a terminal `curses` cannot start was not described → refused like no terminal, naming `solo-sdd config` — a crash would leave the terminal in raw mode
- analyze: the raw keys `integrations` and `integrations.off` are text keys on this screen and bypass the `AGENTS.md` block as `config set` does → kept here; `settings-tui-lists` makes them editable only through its section
