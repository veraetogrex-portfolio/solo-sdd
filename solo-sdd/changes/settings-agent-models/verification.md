## Live Scenario

1. In a temporary project: `python3 -m solo_sdd config set agents.orchestrator-model fable` → code 0; `config describe agents.orchestrator-model` → group `agents`, default `opus`, value `fable`; `config set agents.lookup-model "haiku 4"` → exit 1, the file unchanged.
2. Feed the guard hook (`global/work_hooks.py`, with its `model-policy.json`, under a temporary home) a PreToolUse Agent event in that project: description `Lookup: find the limit`, `subagent_type: Explore`, model `sonnet`, with `agents.lookup-model: sonnet` in the file → a `deny` decision whose reason names `agents.lookup-model` and the `cheap` list.
3. The same event with no project key → allowed.
4. `Orchestrator a` from the main session on `sonnet` with `agents.orchestrator-model: sonnet` → `deny` naming `agents.orchestrator-model` and the `main` list; `Review: a` on `fable` with `agents.review-model: fable` → allowed.
5. A broken `solo-sdd/config` line and `Orchestrator a` on `sonnet` → allowed by the role rules, and a line in the temporary home's `errors.log`.
6. `HOME=<temporary home> python3 sync.py push` → the laid-out `spec-dispatch`, `spec-next` and `~/.claude/CLAUDE.md` name the keys.

Steps 2-5 in one call: `python3 tests/stands/settings-agent-models.py` → `5 of 5 checks passed`.

## Needs

none

## Fallback

not needed.

## Result

<!-- Filled during apply: date, what was run, what was observed. -->

## Not Verified

<!-- Filled during apply: what stayed unproven and why. Write: nothing - if all proven. -->

## Decisions Without Owner

- analyze: the scenario "a cheaper orchestrator on `sonnet`" contradicted the rule that orchestrators stay within `main` (`opus`, `fable`) and the global rule "code on the main model" → the settings example uses `fable`, and an orchestrator on `sonnet` set by the project is denied; an owner who wants `sonnet` orchestrators adds it to the machine `main` list.
- analyze: the hook scenarios (a test model on `opus`, a reviewer on `fable`) gave the same result as today's role rules, so they proved no new code → the hook checks a launch on the project's own model against the role list and names the key; the scenarios use `sonnet`, which today's rules let through for lookup and orchestrator.
- analyze: "a project can narrow the choice" did not say whether a launch on another model in the list is refused → not refused: the skills launch with the project's model, the hook only stops a project value outside the machine list; refusing other in-list models was rejected as a second rule the owner did not ask for.
- analyze: `agents.test-model` mixed the `Lookup:` role with "tests use the cheapest", which `global/AGENTS.md` says of paid product calls in tests → it is the model of those calls; lookups take `agents.lookup-model`; Test model allowlist keeps bounding it, so the hook gets no new test rule.
- analyze: the model keys had no kind, and the `choice` kind with any value is described as "a branch name" → a model name kind: one word of ASCII letters, digits, `.`, `-`, `_`, `[` and `]`.
- analyze: `agents.executor: codex` opens a gate that only the owner's words opened, and an agent can write the line itself → the global rules let an agent change it only on the owner's words in the chat, the same strength as today's rule.
- analyze: main specs `model-guard` (the orchestrator "any model" rule) and `spec-next` (Lead writes code, Reviewer on the main model) contradicted the new refusals, the executor key and a reviewer with a model → `MODIFIED` blocks for these three; `opus` and `/effort low` in `spec-dispatch` scenarios are read as the defaults.
- analyze: the Live Scenario expected exit 2 from the hook, but `deny` prints a `permissionDecision: deny` and exits 0 → the steps check the `deny` decision.
