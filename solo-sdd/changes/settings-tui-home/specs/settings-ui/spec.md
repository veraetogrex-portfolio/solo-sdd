## MODIFIED Requirements

### Requirement: Settings screen
`solo-sdd settings [folder]` on a terminal SHALL open a full-screen screen on the standard library listing every registered key by group with its value in effect and source, and for the selected key its description, allowed values, default and team default. Without a `solo-sdd/` tree it SHALL open only the Machine section and name `solo-sdd init`. Without a terminal on stdin and stdout it SHALL print the command to use instead and exit 1, changing no file.

#### Scenario: Opened in a project
- **WHEN** `solo-sdd settings` runs on a terminal in a project with `solo-sdd/config`
- **THEN** the screen lists the groups and keys with values and sources, and the bottom shows the selected key's description

#### Scenario: No terminal
- **WHEN** `solo-sdd settings < /dev/null` runs
- **THEN** a line naming `solo-sdd config` is printed, exit 1, no file changes

#### Scenario: No tree
- **WHEN** `solo-sdd settings` runs on a terminal in a folder without `solo-sdd/`
- **THEN** the screen shows only the Machine section with a line naming `solo-sdd init`, and `q` leaves with exit 0

#### Scenario: A terminal curses cannot drive
- **WHEN** `solo-sdd settings` runs on a terminal with `TERM=dumb` or a `TERM` the terminal database lacks
- **THEN** the same line naming `solo-sdd config` is printed, exit 1, and no file changes
