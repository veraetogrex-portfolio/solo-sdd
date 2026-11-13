# handlers Specification

## Purpose

Request handlers of the shop service answer from the in-memory store.

## Requirements

### Requirement: User lookup
The `get_user` handler SHALL return the user id and the user name from the store.

#### Scenario: Known user
- **WHEN** `get_user(1)` is called
- **THEN** it returns `{"id": 1, "name": "Ann"}`
