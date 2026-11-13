# Proposal

## Why

`test_get_order` fails: `get_order(7)` returns something other than the stored order.

## What Changes

- `handlers.py`: `get_order` returns the stored order, or `{"error": "not found"}` for a missing id.

## Capabilities

### New Capabilities

### Modified Capabilities
- `handlers`: order lookup.

## Impact

`handlers.py`.

## Out of Scope

- The user handler.

## Depends On

none

## Source

"Fix the order handler" (owner).
