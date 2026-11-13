## Purpose

Prints the tip and the total of a restaurant bill for a given tip percent, rounded to cents.

## ADDED Requirements

### Requirement: Tip and total
`python3 tip.py <bill> <percent>` SHALL print one line `tip <tip>, total <total>`, where the tip is the bill times the percent divided by 100, rounded half up to cents, and the total is the bill plus that tip, and exit with code 0.

#### Scenario: A usual bill
- **WHEN** the user runs `python3 tip.py 40 15`
- **THEN** it prints `tip 6.00, total 46.00`

#### Scenario: Rounding half up
- **WHEN** the user runs `python3 tip.py 10.10 15`
- **THEN** it prints `tip 1.52, total 11.62`

### Requirement: Wrong input
A bill or a percent that is not a non-negative number SHALL be refused with a message on stderr and exit code 2, printing nothing on stdout.

#### Scenario: A negative bill
- **WHEN** the user runs `python3 tip.py -5 15`
- **THEN** it exits with code 2 and stderr names the bill
