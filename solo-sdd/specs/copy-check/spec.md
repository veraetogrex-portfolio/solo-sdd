# copy-check Specification

## Purpose
A check of text people read in a product (interface strings, a landing page, README, release notes, error messages): the "draft → audit → final" loop by the anti-slop rules without new facts, rules by language, specific buttons and the priority of the owner's sample.

## Requirements

### Requirement: Copy check cycle
`copy-check` SHALL put every text through a draft, an audit and a final. The audit answers two questions: "what gives away AI in the text" and "does the text hold a fact, name, number, date or quote that is not in the source and in the project". The final SHALL NOT hold facts that are not in the source or in the project. Where the text does not work without a fact, the placeholder `[data needed: <what>]` is put.

#### Scenario: An invented number
- **WHEN** an interface string is "Trusted by 10,000 teams worldwide", and the project has no source for the number
- **THEN** the final has no number: the line is removed or replaced with `[data needed: number of customers]`, the report names the reason

### Requirement: Clusters not single tells
`copy-check` SHALL fix clusters of AI-text signs: two or more different signs in one paragraph or interface string. A single sign from the "do not flag" list of `antislop-copywriting` SHALL NOT be fixed. The core bans R-02 (English only), R-15, R-16 and R-17 are fixed in every occurrence, even a single one.

#### Scenario: A single sign
- **WHEN** the README has one "However" and no other signs
- **THEN** the line does not change

#### Scenario: A single core ban
- **WHEN** `en.json` has one line "Fast — and simple", without other signs in it
- **THEN** the dash is replaced (R-02), the rest is untouched

### Requirement: Rules by language
`copy-check` SHALL check English text by the `antislop-copywriting` patterns with R-02 and R-16. Text in another language SHALL go through the facts audit and the "do not flag" list, and through a style skill for that language only if the agent has one; `copy-check` SHALL NOT name a particular style skill. R-02 and the English word lists SHALL NOT apply to Russian text.

#### Scenario: A dash in two languages
- **WHEN** `en.json` has "Fast — and simple", and `ru.json` has the user's Russian sentence with an em dash
- **THEN** the English line is fixed, the Russian one is untouched

#### Scenario: No style skill for the language
- **WHEN** `copy-check` runs in Codex, which has no style skill for Russian
- **THEN** Russian text goes only through the facts audit and the "do not flag" list, the report names it with the line "Other languages: Russian: without a style skill"

### Requirement: Specific buttons
R-15 SHALL apply to buttons in both languages: a button that does not name an action ("Get Started", "Learn More", and Russian buttons like "Start", "Learn more", "Try", "Next" without context) gets an action verb from the source: the label next to it, the handler or the project README.

#### Scenario: Generic buttons
- **WHEN** the buttons are "Get Started" and a Russian "Start", and the stand README says they create the first note
- **THEN** both are replaced with a text about creating a note

### Requirement: Owner sample outranks rules
If the owner gave a sample of their text, `copy-check` SHALL adapt to the sample (phrase length, vocabulary, punctuation), not only clean out signs. The sample wins over the style rules (phrase length, vocabulary, punctuation, R-02); a deviation from R-02 SHALL be recorded in the report. The sample SHALL NOT cancel the facts audit and R-17, R-36, R-38.

#### Scenario: A sample with dashes
- **WHEN** the owner's English sample often uses the em dash
- **THEN** the final keeps dashes at the sample's frequency, the report names the deviation from R-02

### Requirement: UI strings through copy-check
`ui-check` SHALL pass to `copy-check` the interface strings the change created or changed (by `git diff` from the base branch: string files and text in markup) before the gate, and SHALL include in the report the "Texts" line with the `copy-check` result. The gate reads the already fixed text; R-02, R-15 and R-16 are not flagged again for these strings.

#### Scenario: A change edits button labels
- **WHEN** a change edited three strings in `en.json`
- **THEN** the `ui-check` report has the "Texts" line with the result for these three strings, and the gate does not duplicate R-02, R-15 and R-16 for them

### Requirement: Copywriting rules laid out
`antislop-copywriting` SHALL be kept in `integrations/antislop/skills/antislop-copywriting/` and deployed by `sync.py push` together with the core into `<root>/copy-check/antislop/` of all three roots; the entry of `integrations/antislop/antislop.md` in `targets.json["files"]` names `copy-check` with the path `antislop/core.md`, next to `ui-check`. The `copy-check` skill SHALL be deployed into all three roots.

#### Scenario: Deployment
- **WHEN** after `python3 sync.py push` `python3 sync.py status` is run
- **THEN** `copy-check/SKILL.md`, `copy-check/antislop/core.md` and `copy-check/antislop/copywriting.md` are `ok` in all three roots
