## MODIFIED Requirements

### Requirement: Edit by type
Editing a key SHALL offer a pick list for a choice, a number entry for a whole number, checkboxes for a list with known values, and a text entry for other lists, names and paths. Every entered value SHALL pass the same check as `config set`; a refused value SHALL keep the old one and show the reason. Reset SHALL put the key back to the value below the file. A text entry longer than the screen SHALL show the end of the value and the cursor.

#### Scenario: A choice
- **WHEN** the person selects `delivery.mode`, presses Enter and picks `pr`
- **THEN** the key shows `pr` marked as unsaved

#### Scenario: A wrong number
- **WHEN** the person enters `0` for `dispatch.limit`
- **THEN** the reason from the settings check is shown and the old value stays

#### Scenario: Checkboxes
- **WHEN** the person unticks `codex` on `agents`
- **THEN** the value becomes the other ticked agents in registry order

#### Scenario: Reset
- **WHEN** the file has `dispatch.limit: 4` and the person resets the key
- **THEN** the key shows `2` with source `default`, marked as unsaved

#### Scenario: A long text entry
- **WHEN** the person types 150 characters into the entry of `delivery.deploy` on an 80-column screen
- **THEN** the entry line shows the last characters typed and the `_` cursor, and the value keeps all 150 characters
