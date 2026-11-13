# Project

Language: en
Mode: prod

Intent: solo-sdd is a spec-driven development process for one person or a team, with any coding
agent (Claude Code and Codex today): algorithm, skills, global rules, hooks, templates and an own
process format with its validator in one repository, independent of other spec tools.
Success means an agent takes a change from plan to merged main without questions to the owner, and readiness
is proven by a live check, not by a report.

## Apply rules

- Paid calls to the product model in tests and live acceptance use the cheapest models; review and acceptance use the main model
- Readiness is proven by a scenario in what a person receives, not by green unit tests
- A change in global/ or skills/ reaches the agents only after sync.py push; the live scenario runs after the layout
