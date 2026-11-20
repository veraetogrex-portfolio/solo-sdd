## MODIFIED Requirements

### Requirement: Review rounds
The first acceptance round SHALL read the whole change diff; every later one only the diff since the last round and the open findings' places, with the given findings, which the reviewer does not repeat. At most `process.review-rounds` rounds (default 5) SHALL run, plus Extra round for fix findings. An `Important` left then means no archive: the findings and "reconsider the approach" go into `Not Verified`. The reviewer gets `REVIEW.md` without `## Unconfirmed`; the report names the rounds.

#### Scenario: The second round
- **WHEN** after the first round the author fixed one `Important` finding
- **THEN** the second-round reviewer gets the diff since the first round and the list of given findings; it does not repeat a finding it already gave

#### Scenario: The review did not converge
- **WHEN** `process.review-rounds` is not set, and after the fifth round an `Important` remains on a line the last rework did not change
- **THEN** there is no sixth round, the change is not archived, `Not Verified` has the finding and "reconsider the approach"

#### Scenario: The project's review rules
- **WHEN** the project root has `REVIEW.md`
- **THEN** the reviewer gets it without its `## Unconfirmed` section, together with the delta specs

#### Scenario: A project limit
- **WHEN** the project's `solo-sdd/config` has `process.review-rounds: 2`, and after the second round an `Important` remains outside the last rework
- **THEN** there is no third round and the change is not archived

#### Scenario: Unconfirmed review rules
- **WHEN** the project's `REVIEW.md` has three rules and a `## Unconfirmed` section with one line
- **THEN** the reviewer gets the three rules and not the unconfirmed line
