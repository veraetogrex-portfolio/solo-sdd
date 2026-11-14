## Live Scenario

In a temporary git repository with a temporary `HOME`:

1. `solo-sdd init --yes < /dev/null`, then `solo-sdd doctor | grep project-rules` → `ok project-rules:`.
2. Simulate an older version: replace one line of the rules inside the block and write the digest of the new block body into `solo-sdd/rules-block` (what an older `init` would have left), then `solo-sdd doctor | grep project-rules` → `warn project-rules:` naming `solo-sdd init`; `AGENTS.md` keeps its bytes (compare a hash before and after).
3. `solo-sdd init < /dev/null`, then `doctor` → `ok project-rules:`.
4. Edit a line inside the block without touching the record → `warn project-rules:` naming the block as edited in place and the rules path, no `solo-sdd init`.
5. `solo-sdd config set rules.scope global` → `doctor` prints no `project-rules` line.

## Needs

none

## Fallback

Not needed: every step runs locally.

## Result

<!-- Filled during apply: date, what was run, what was observed. -->

## Not Verified

<!-- Filled during apply: what stayed unproven and why. Write: nothing - if all proven. -->

## Decisions Without Owner

- plan: the owner asked to think ahead about updates → a project's rules block left at an older version is named by `doctor` — after an update the agents of every prepared project would otherwise keep the old rules unnoticed
