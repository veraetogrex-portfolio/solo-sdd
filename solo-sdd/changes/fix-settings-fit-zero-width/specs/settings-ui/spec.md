## MODIFIED Requirements

### Requirement: Safe display
Text read from the config or the registry SHALL be shown with control characters escaped. A terminal under 40 columns or 12 rows SHALL show a request to enlarge it; a wider one SHALL cut long lines to its width without breaking the layout.

#### Scenario: An escape in a value
- **WHEN** a comment or a value holds an ESC character
- **THEN** the screen shows it as `\x1b` and the terminal state does not change

#### Scenario: A small terminal
- **WHEN** the terminal is 30 columns wide
- **THEN** the screen shows only the request to enlarge it, and redraws the list after a resize to 80

#### Scenario: Zero-width marks
- **WHEN** a value holds `กั` five times (Thai, five columns), and the line has five free columns
- **THEN** the line keeps all ten characters, as a zero-width mark takes no column

#### Scenario: An emoji with a presentation selector
- **WHEN** a value holds U+2764 U+FE0F three times, and the line has six free columns
- **THEN** the line keeps all six characters and takes no more than six columns, as U+FE0F still counts one column
