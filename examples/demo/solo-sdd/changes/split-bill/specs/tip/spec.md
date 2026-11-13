## ADDED Requirements

### Requirement: Split between people
With `--people <n>`, `tip.py` SHALL print a second line `each <share>`, where the share is the total divided by `n` and rounded up to a cent. Without `--people` the output SHALL stay one line. A value of `--people` that is not a whole number from 1 SHALL be refused with a message on stderr and exit code 2, printing nothing on stdout.

#### Scenario: Four people
- **WHEN** the user runs `python3 tip.py 40 15 --people 4`
- **THEN** it prints `tip 6.00, total 46.00` and then `each 11.50`

#### Scenario: A share rounded up
- **WHEN** the user runs `python3 tip.py 100 0 --people 3`
- **THEN** the second line is `each 33.34`

#### Scenario: Zero people
- **WHEN** the user runs `python3 tip.py 40 15 --people 0`
- **THEN** it exits with code 2, stdout is empty and stderr says that `--people` must be a whole number from 1
