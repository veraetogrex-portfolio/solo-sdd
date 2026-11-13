# ui-direction Specification

## Purpose
The project's interface direction: a `DESIGN.md` the owner fills in, a Design Read line in a UI change, a live scenario by element and placeholders instead of the owner's data.

## Requirements

### Requirement: Interface project
`project-init` SHALL count a project as one with an interface if outside `node_modules/`, `tests/`, `solo-sdd/` and hidden folders (`.git/`, `.venv/`) there is a file with an extension from the `UI_EXT` list of the hook `global/work_hooks.py` (`.html .htm .css .scss .sass .less .tsx .jsx .vue .svelte`), or if the owner explicitly named an interface in the request (a site, a landing page, an app with screens). Otherwise `DESIGN.md` is not created.

#### Scenario: A project without an interface
- **WHEN** `project-init` runs in the repository of a CLI utility without markup and styles
- **THEN** `DESIGN.md` is not created

#### Scenario: An empty folder
- **WHEN** `project-init` runs in an empty folder without words about an interface in the request
- **THEN** `DESIGN.md` is not created

### Requirement: Project design direction
`project-init` in a project with an interface SHALL create `DESIGN.md` by the template `templates/DESIGN.md` and an "Interface" section in the project's `AGENTS.md` with a link to it. The fields are filled only with the owner's answers. Unfilled fields stay empty, a `Dial` line with the letters `n` instead of numbers counts as an empty field. If there are empty fields, the `docs/waiting.md` table gets one line about them; if there are none, there is no line.

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
A repeated run of `project-init` SHALL keep the existing `DESIGN.md`: filled fields do not change, missing fields are added empty, empty fields are filled only with the owner's answers from this request, and the line about `DESIGN.md` in `docs/waiting.md` is updated, not duplicated; if no empty fields are left, the line is deleted.

#### Scenario: A repeated run
- **WHEN** `project-init` runs again in a folder where the owner already filled part of `DESIGN.md`
- **THEN** the filled fields did not change, missing fields are added empty, there is one line about `DESIGN.md` in `docs/waiting.md`

#### Scenario: No empty fields left
- **WHEN** `project-init` runs again, and the owner filled all fields of `DESIGN.md`, including the numbers in the `Dial` line
- **THEN** `DESIGN.md` did not change, `docs/waiting.md` has no line about it

### Requirement: Direction predicate
The interface direction SHALL count as set only if `DESIGN.md` has the line `Dial: ENERGY n / RHYTHM n / MOTION n` with three numbers from 1 to 3. The agent SHALL NOT derive dials from the owner's words. If the direction is not set, everywhere dials are needed, ENERGY 1 / RHYTHM 1 / MOTION 1 is put with the mark "draft without direction".

#### Scenario: Words exist, the Dial line has no numbers
- **WHEN** `DESIGN.md` has the character, theme and palette filled, and there is no `Dial` line or it has the template `n` instead of numbers
- **THEN** the dials are ENERGY 1 / RHYTHM 1 / MOTION 1 with the mark "draft without direction"

### Requirement: Design Read in UI change
`spec-plan` SHALL start What Changes of every change that changes the interface with a Design Read line: "Design Read: <screen> for <audience>, <style>, ENERGY n / RHYTHM n / MOTION n". The audience comes from the "Audience" field, the style from the "Character" field; the dials and the mark by the requirement Direction predicate; an empty field or no `DESIGN.md` is written in the Design Read as "not specified". A bug fix (the "Bug fix" section of `spec-plan`) gets no Design Read.

#### Scenario: There is a direction
- **WHEN** `DESIGN.md` has "Dial: ENERGY 2 / RHYTHM 3 / MOTION 1", and the plan asks for a new settings screen
- **THEN** the first item of What Changes is a Design Read with ENERGY 2 / RHYTHM 3 / MOTION 1 without the mark

#### Scenario: No direction
- **WHEN** there is no `DESIGN.md`, and the plan asks for a landing page
- **THEN** the Design Read holds ENERGY 1 / RHYTHM 1 / MOTION 1 and "draft without direction"

### Requirement: UI live scenario by element
`spec-plan` SHALL write the Live Scenario of a change that changes the interface as a list "element → action → expected result" for every control the change creates or changes, with widths 1280 and 390 and every theme the interface supports. In a bug fix the list holds only the affected elements.

#### Scenario: A form and a menu
- **WHEN** a change adds a subscription form and a mobile menu to an interface with a light and a dark theme
- **THEN** the Live Scenario has the lines "empty form → submit → a message about the unfilled field", "valid email → submit → a success message", "menu at 390 → open and close → opens and closes" and a check of both themes

### Requirement: Owner data as placeholders
`spec-plan` SHALL NOT write into tasks and scenarios numbers, reviews, customer names, logos and photos of people that are not in `Source` or in project files. Instead the tasks require the placeholder `[data needed: <what>]`, `Needs` lists the needed data, and their `Fallback` is "the placeholder stays on screen". The change SHALL stay doable without this data and gets no `WAITING` file.

#### Scenario: A landing page with reviews
- **WHEN** the plan asks for "a landing page with customer reviews and growth numbers", and there is no data in the message or the project
- **THEN** the tasks require blocks with the placeholders `[data needed: customer reviews]` and `[data needed: growth numbers]`, `Needs` has both items, `Fallback` keeps the placeholders on screen, there is no `WAITING` file

#### Scenario: A landing page in demo mode
- **WHEN** the same plan goes in a project with mode `demo`
- **THEN** reviews and growth numbers stay placeholders `[data needed: …]`

#### Scenario: Working data in demo mode
- **WHEN** a change in `demo` mode needs product data
- **THEN** the rule applies here too: the product's working data is invented (a seed, an emulation), but not the owner's numbers, reviews and customers
