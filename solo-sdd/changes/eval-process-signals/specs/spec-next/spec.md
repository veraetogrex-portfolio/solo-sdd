## ADDED Requirements

### Requirement: Review verdict line
The answer of every `Review:` agent of step 7a SHALL end with the line `Important: <n>`: the `Important` findings open after this round, new ones and given ones not closed (closed: fixed in the diff, or dropped with the reason the author gives in the list of given findings), `0` when none. The author SHALL gate rework, rounds and the archive on that line; an answer without it SHALL be a reviewer failure: the round has no verdict.

#### Scenario: A round with one open finding
- **WHEN** a reviewer closes both findings of the last round and gives one new `Important` finding
- **THEN** its answer ends with the line `Important: 1`

#### Scenario: A clean round
- **WHEN** a reviewer gives only `Nit` findings
- **THEN** its answer ends with the line `Important: 0`

#### Scenario: A given finding still open
- **WHEN** in round 2 a reviewer finds the round-1 `Important` finding not fixed and gives no new one
- **THEN** its answer ends with the line `Important: 1`

#### Scenario: No verdict line
- **WHEN** a reviewer's answer has no line `Important: <n>`
- **THEN** acceptance counts it as a reviewer failure and reruns the reviewer once; a second such answer in the round means no archive, with the missing line in `Not Verified`
