=== solo-sdd/changes/bookkeeper-rounding/proposal.md
# Proposal

## Why

Practitioner checks: exact decimal arithmetic — https://docs.python.org/3/library/decimal.html; minor units of the currency — ISO 4217; round half to even — IEEE 754

## What Changes

- An exact half cent rounds to the even cent.

=== solo-sdd/changes/bookkeeper-rounding/tasks.md
- [ ] 1.1 Use decimal arithmetic, the currency minor units and round half to even in `tip.py`.
