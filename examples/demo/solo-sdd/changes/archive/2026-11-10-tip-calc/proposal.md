# Proposal

## Why

Splitting a restaurant bill starts with the tip, and doing it in the head gives wrong cents. A command that prints the tip and the total for a bill and a percent closes that.

## What Changes

- `python3 tip.py <bill> <percent>` prints `tip <tip>, total <total>` with two decimals.
- A bill or a percent that is not a non-negative number is refused with a message and exit code 2.

## Capabilities

### New Capabilities
- `tip`: the tip and total of a bill.

### Modified Capabilities

## Impact

`tip.py`, `tests/test_tip.py`.

## Out of Scope

- Splitting the total between people: the next change.

## Depends On

none

## Source

"I want to type the bill and the percent and see the tip and the total" (the demo owner, 10.11.2026)
