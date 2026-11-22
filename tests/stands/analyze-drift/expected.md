# The reference report of add-retry

The report a run that finds every planted hole and nothing else would hand back.

analyze add-retry: requirements 2, scenarios 3, tasks 5; covered 3/3
CRITICAL 0 · HIGH 3 · MEDIUM 0 · LOW 0, fixed 0

Retell:
- `backup.py` tries a failed copy again, up to a retry limit, and prints the number of tries or that it gave up.
- The retry limit comes from `backup.json`, with a default when it sets none.

| ID | Pass | Level | Where | Finding | What was done |
|---|---|---|---|---|---|
| 1 | 7 | HIGH | tasks.md 1.2, Requirement: Default retry limit | The task says default `5`, the requirement `3` | |
| 2 | 7 | HIGH | tasks.md 1.3, Scenario: A limit the person set | The task reads `process.retry-limit`, the scenario names `process.retry-max` for the same limit | |
| 3 | 1 | HIGH | proposal.md What Changes, `docs/retry.md` | No retell line, task or requirement covers the promised `docs/retry.md` | |

Ready for implementation: no — three HIGH.
