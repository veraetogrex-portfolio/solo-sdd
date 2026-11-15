## MODIFIED Requirements

### Requirement: Review rounds
The first acceptance round SHALL read the whole change diff; every later one only the diff since the last round and the open findings' places, with the list of given findings, which the reviewer does not repeat. At most `process.review-rounds` rounds (default 5) SHALL run, plus Extra round for fix findings. An `Important` left then means no archive: the findings and "reconsider the approach" go into `Not Verified`. The reviewer gets `REVIEW.md` if any; the report names the rounds.

#### Scenario: The second round
- **WHEN** after the first round the author fixed one `Important` finding
- **THEN** the second-round reviewer gets the diff since the first round and the list of given findings; it does not repeat a finding it already gave

#### Scenario: The review did not converge
- **WHEN** `process.review-rounds` is not set, and after the fifth round an `Important` remains on a line the last rework did not change
- **THEN** there is no sixth round, the change is not archived, `Not Verified` has the finding and "reconsider the approach"

#### Scenario: The project's review rules
- **WHEN** the project root has `REVIEW.md`
- **THEN** the reviewer gets it together with the delta specs

#### Scenario: A project limit
- **WHEN** the project's `solo-sdd/config` has `process.review-rounds: 2`, and after the second round an `Important` remains outside the last rework
- **THEN** there is no third round and the change is not archived

## ADDED Requirements

### Requirement: Extra round for fix findings
When the last round is the second or later and every `Important` open after it has all its places in lines the rework before that round changed, one more round SHALL run without asking the owner. An `Important` left after it SHALL mean no archive as in Review rounds; there SHALL be no second extra round. The report SHALL say whether the extra round ran.

#### Scenario: A finding on the fix
- **WHEN** after the fifth round the only open `Important` is on a line the fourth-round rework added
- **THEN** a sixth round runs without a question to the owner, and the report says the extra round ran

#### Scenario: The extra round did not close it
- **WHEN** after the extra round an `Important` remains
- **THEN** there is no further round, the change is not archived, `Not Verified` has the finding and "reconsider the approach"

#### Scenario: A limit of one round
- **WHEN** `process.review-rounds` is 1 and an `Important` remains after the first round
- **THEN** no extra round runs, and the change is not archived

#### Scenario: A finding outside the fix
- **WHEN** after the last round one open `Important` is on a line the last rework did not change
- **THEN** no extra round runs, and the change is not archived
