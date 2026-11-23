## Purpose
The result of an analysis, a research or a data pull reaches the owner as actions with their expected effect, and its data as a file the owner can open, never only inside a tool.

## ADDED Requirements

### Requirement: Analysis opens with actions and their effect
Section 1 of the global rules SHALL hold that the result of a request to analyse, research or pull data opens, within its first 5 non-empty lines, with one to three actions written `<action> — <expected effect for the owner>` (a number when there is one), or with a line `No action follows:` and the reason; for such a report these lines take the place of the 2-4 plain lines of section 1.

#### Scenario: An analysis of a catalog
- **WHEN** an agent with the global rules is asked "analyse the catalog" and the data lies in a SQLite file of the project
- **THEN** within the first 5 non-empty lines of its answer stand one to three list items, each holding ` — ` and an effect after it

#### Scenario: No data
- **WHEN** the same agent is asked to analyse a catalog whose table has no rows
- **THEN** within the first 5 non-empty lines of its answer stands a line starting with `No action follows:` and a reason

### Requirement: Goal lines before the actions
For a request of steps without a goal, the `Goal:` and `Check:` lines of section 6 of the global rules SHALL come first and the actions right after them; the 5-line windows of section 1 SHALL count the non-empty lines after the `Goal:` and `Check:` lines, and section 1 SHALL state this order.

#### Scenario: A step-only analysis
- **WHEN** the agent is asked "count the rows of catalog.db and list the five oldest items", with no reason
- **THEN** the answer opens with the `Goal:` and `Check:` lines and the next non-empty lines are the actions

### Requirement: Analysis data delivered as a file
Section 1 of the global rules SHALL hold that the data and the full analysis go into a Markdown or CSV file in the project folder (with no project, in the session folder), linked within the first 5 non-empty lines of the answer; data kept only inside a tool, a database or an MCP server SHALL NOT count as delivered.

#### Scenario: Data only in a database
- **WHEN** the same agent finishes the analysis of the catalog whose rows exist only in the SQLite file
- **THEN** within the first 5 non-empty lines its answer links a Markdown or CSV file in the project folder, and that file exists and holds the actions

### Requirement: Analysis file allowed
Sections 3 and 6 of the global rules SHALL name the file of Analysis data delivered as a file as the one file an analysis, a research or an assessment writes, besides a `## Lessons` edit of section 15; every other file of the project SHALL stay unchanged, and the file is committed only when the project's rules or section 13 commit work.

#### Scenario: Only the analysis file
- **WHEN** the agent finishes the analysis of the catalog
- **THEN** `git status --porcelain` of the catalog project lists only the analysis file, or nothing when the only new commit adds only that file
