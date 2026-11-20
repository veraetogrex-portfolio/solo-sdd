## Live Scenario

The stand lays the real `global/work_hooks.py` and `global/model-policy.json` of the working folder into a temporary HOME as `~/.claude/hooks/` and runs the hook as Claude Code runs it, on `/usr/bin/python3`, with `PreToolUse` events from a temporary git project (the form of `tests/stands/settings-agent-models.py`).

1. `python3 sync.py push`, then `python3 sync.py status` → the layout of `~/.claude/hooks/work_hooks.py` and `model-policy.json` matches the repository, no unexpected `drift`.
2. `python3 tests/stands/subagent-check-roles.py` → from a subagent (`agent_id` set): `Analyze: a` without `model` allow; `Check: a` on `opus` allow; `Judge: a` on `haiku` deny naming the `main` list; `Attack: a 4 4a` on `haiku` with `subagent_type: general-purpose` allow; `Attack: a` without `model` deny and on `opus` deny, both naming a cheap model set explicitly; `Implement: a` deny naming the six allowed tags.
3. The same stand with `agents.attack-model: sonnet` in the project's `solo-sdd/config` and `Attack: a` on `sonnet` → deny naming `agents.attack-model` and the `cheap` list; with `agents.review-model: fable` and `Judge: a` on `fable` → allow.
4. The same stand writes a transcript with an edit of `src/app.py` followed by `Analyze:`, `Attack:`, `Judge:` and `Check:` agents and runs `solo-sdd archive a --yes` through the hook → deny naming `src/app.py`; with a `Review: a` agent appended after them → allow.
5. The stand prints its summary: `subagent-check-roles: 4 of 4 checks passed`.

## Needs

none

## Fallback

Not needed: the stand runs locally on the hook, without model calls or access.

## Result

<!-- Filled during apply: date, what was run, what was observed. -->

## Not Verified

<!-- Filled during apply: what stayed unproven and why. Write: nothing - if all proven. -->

## Decisions Without Owner

<!-- Filled during apply: choices made without asking, and new changes created for out-of-scope work. -->

- analyze: which subagent type an attacker may use → any `subagent_type`, like a reviewer, not only `Explore` — attackers read the artifacts and main specs, and the cheap model rule is what bounds their cost.
- analyze: which key bounds `Analyze:`, `Judge:` and `Check:` → `agents.review-model` and the `main` list — they are judgement on the main model, as review is, and a fourth model key would add nothing.
