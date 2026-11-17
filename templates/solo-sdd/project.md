# Project

Language: en
Mode: prod

A value set by `solo-sdd config set` for `project.stage` (Mode) or `artifacts.language` (Language) wins over these two lines.

Intent: <2-3 sentences: what this is, for whom and what counts as success. Every new change
is checked against it; a change that leads away from the intent is not created.>

## Apply rules

- Paid calls to the product model in tests and live acceptance use the cheapest models; review and acceptance use the main model
- Readiness is proven by a scenario in what a person receives, not by green unit tests
