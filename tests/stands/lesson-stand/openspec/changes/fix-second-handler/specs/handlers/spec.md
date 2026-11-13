## ADDED Requirements

### Requirement: Order lookup
The `get_order` handler SHALL return the stored order for a known id and `{"error": "not found"}` for an unknown id.

#### Scenario: Known order
- **WHEN** `get_order(7)` is called
- **THEN** it returns `{"id": 7, "user": 1, "total": 30}`

#### Scenario: Unknown order
- **WHEN** `get_order(99)` is called
- **THEN** it returns `{"error": "not found"}`
