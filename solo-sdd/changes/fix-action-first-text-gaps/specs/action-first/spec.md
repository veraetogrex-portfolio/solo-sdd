## MODIFIED Requirements

### Requirement: Goal lines before the actions
For a request of steps without a goal, the `Goal:` and `Check:` lines of section 6 of the global rules SHALL come first and the actions or the `No action follows:` line right after them, also for a lookup with nothing to fix (the data gives no action, as a table with no rows), unless a form the request or a running skill prescribes puts another line first; the 5-line windows of section 1 SHALL count the non-empty lines after the `Goal:` and `Check:` lines, and section 1 SHALL state this order.

#### Scenario: A step-only analysis
- **WHEN** the agent is asked "count the rows of catalog.db and list the five oldest items", with no reason
- **THEN** the answer opens with the `Goal:` and `Check:` lines and the next non-empty lines are the actions

#### Scenario: A step-only lookup with nothing to fix
- **WHEN** the agent is asked "count the rows of catalog.db and list the five oldest items", with no reason, on a catalog whose table has no rows (nothing to fix)
- **THEN** the answer opens with the `Goal:` and `Check:` lines, and the next non-empty line starts with `No action follows:`

### Requirement: Analysis data delivered as a file
Section 1 of the global rules SHALL hold that the data and the full analysis go into a Markdown or CSV file in the project folder that holds the same action lines (with no project, in the session folder), a new file each time, never overwriting one, linked within the first 5 non-empty lines of the answer (an answer whose actions window holds `No action follows:`, or a failed read, needs none); data kept only inside a tool, a database or an MCP server SHALL NOT count as delivered.

#### Scenario: Data only in a database
- **WHEN** the same agent finishes the analysis of the catalog whose rows exist only in the SQLite file
- **THEN** within the first 5 non-empty lines its answer links a Markdown or CSV file in the project folder, and that file exists and holds the actions
