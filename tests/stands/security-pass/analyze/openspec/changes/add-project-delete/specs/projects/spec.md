## ADDED Requirements

### Requirement: Delete a project
`DELETE /projects/{id}` SHALL remove the project with that id and its files and answer `204`.

#### Scenario: Deleted
- **WHEN** `DELETE /projects/7` is called and project 7 exists
- **THEN** the answer is `204` and `GET /projects/7` answers `404`
