# Proposal

## Why

At a table of several people everyone asks "how much is mine?": `tip.py` prints only the whole total, and dividing it in the head loses cents, so the shares come out short of the bill.

## What Changes

- `python3 tip.py <bill> <percent> --people <n>` also prints `each <share>`: the total divided by `n`, rounded up to a cent.
- `--people` that is not a whole number from 1 is refused with a message and exit code 2.

## Capabilities

### New Capabilities

### Modified Capabilities
- `tip`: a new requirement "Split between people"; the existing requirements do not change.

## Impact

`tip.py`, `tests/test_tip.py`.

## Out of Scope

- Uneven shares and per-person tips.
- Currencies other than two-decimal ones.

## Depends On

none

## Source

"we are four at the table, I want to see what each of us pays" (the demo owner, 10.11.2026)
