## MODIFIED Requirements

### Requirement: Project design direction
`project-init` in a project with an interface SHALL create `DESIGN.md` by the template `templates/DESIGN.md` and an "Interface" section in the project's `AGENTS.md` with a link to it. The fields are filled only with the owner's answers. Unfilled fields stay empty, a `Dial` line with the letters `n` instead of numbers counts as an empty field. If there are empty fields, the first table of `docs/waiting.md` gets one line about them; if there are none, there is no line.

#### Scenario: A new project without owner answers
- **WHEN** `project-init` runs in a folder with `index.html`, and the owner said nothing about the style
- **THEN** `DESIGN.md` is created with empty fields, `docs/waiting.md` has one line about it, `AGENTS.md` has an "Interface" section with a link; the agent filled no field

#### Scenario: The owner described the style in the chat
- **WHEN** the owner wrote in the same message "calm, dark theme, one orange accent"
- **THEN** these words are carried into the character, theme and palette fields, the other fields are empty, the line in `docs/waiting.md` lists the empty fields

#### Scenario: The form of the waiting line
- **WHEN** `DESIGN.md` has empty fields left
- **THEN** the line in `docs/waiting.md`: Change `—`, Items `—`, Waiting for "DESIGN.md: fill in the fields <list of empty fields>", From whom: the owner, Since: the date; there is no `WAITING` file, because there is no change

#### Scenario: No docs/waiting.md
- **WHEN** there are empty fields, and there is no `docs/waiting.md`
- **THEN** the file is created by the template `templates/docs/waiting.md`, with a line about the empty fields

### Requirement: Design file rerun
A repeated run of `project-init` SHALL keep the existing `DESIGN.md`: filled fields do not change, missing fields are added empty, empty fields are filled only with the owner's answers from this request, and the line about `DESIGN.md` in the first table of `docs/waiting.md` is updated, not duplicated, or added when absent; if no empty fields are left, that line moves to `## Closed` with the evidence `DESIGN.md: no empty fields` and the date, never deleted.

#### Scenario: A repeated run
- **WHEN** `project-init` runs again in a folder where the owner already filled part of `DESIGN.md`
- **THEN** the filled fields did not change, missing fields are added empty, there is one line about `DESIGN.md` in the first table of `docs/waiting.md`

#### Scenario: No empty fields left
- **WHEN** `project-init` runs again, the first table of `docs/waiting.md` has the line about `DESIGN.md`, and the owner filled all fields of `DESIGN.md`, including the numbers in the `Dial` line
- **THEN** `DESIGN.md` did not change, the first table of `docs/waiting.md` has no line about it, and `## Closed` holds that line with the evidence `DESIGN.md: no empty fields` and the date

#### Scenario: An empty field after the closing
- **WHEN** the line about `DESIGN.md` is under `## Closed`, and a repeated run adds a missing field empty
- **THEN** the first table gets one new line about `DESIGN.md`, and the `## Closed` line stays as it was
