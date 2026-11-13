# projects Specification

## Purpose

An HTTP service where signed-in users keep projects; a project belongs to the user who created it.

## Requirements

### Requirement: List own projects
`GET /projects` SHALL return the projects of the signed-in user only.

#### Scenario: Two users
- **WHEN** users A and B each have a project and A calls `GET /projects`
- **THEN** the answer holds only the project of A
