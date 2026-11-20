# Proposal

## Why

`sdd-eval.py` counts a change as done when it is merged and the oracle tests pass on the result. A run that guessed right without an honest path (no review after the last code edit, a `LIVE` command that is not the Live Scenario's, no `spec-analyze` pass) scores the same as one that followed the process, so a configuration that skips steps can look as good as one that keeps them. The signals of the path are already in the data the metrics read: the session journals of the dispatcher and its subagents, and the copy's `verification.md`. Counting them needs no paid run.

## What Changes

- `sdd-eval.py metrics` adds, for every copy, the signals of the path: whether a `Review:` agent came after the last code edit of the orchestrator, the number of review rounds and of `Important` findings in their results, whether the `LIVE` command of the accepted status is a code span of the copy's Live Scenario (by the same reader `sdd-dispatch.py accept` uses), and the `spec-analyze` count from the orchestrator's `Analyze:` report line, `null` when the line is missing.
- The subagent count by role adds `lookup`, `analyze`, `attack`, `judge` and `check`.
- `sdd-eval.py compare` shows the signals per change and run next to `done`, and marks `done, path incomplete` a change that is done but has no review after the last edit or a `LIVE` outside the Live Scenario, and `done, path unknown` one whose signals could not be read.
- `tests/eval/README.md` describes the signals and how each is read.

## Capabilities

### New Capabilities

### Modified Capabilities
- `dispatch-eval`: ADDED requirements Process path signals, What the signals read; MODIFIED requirement Metrics by one method.

## Impact

- `global/sdd_eval.py`
- `tests/test_sdd_eval.py`
- `tests/eval/fixtures/`
- `tests/affected.json`
- `tests/stands/eval-process-signals.py`
- `tests/eval/README.md`

## Out of Scope

- A replay run of the set and the eval baseline: they need 4-7 h and about $80-200 per run and wait in `docs/waiting.md` (`dispatch-eval-replay`).
- Changing the "done" rule (merged and oracle green): the signals stand next to it.
- Neighbouring changes of this plan: `subagent-check-roles`, `analyze-outside`, `outside-check-text`, `source-over-paste`, `goal-first`, `practitioner-techniques`, `skill-ablation`, `work-pull`, `review-principles`.

## Depends On

- subagent-check-roles
- analyze-outside
- practitioner-techniques

## Source

The owner, 2026-11-20 (translated from Russian): "A separate small unit `eval-process-signals`: in `sdd-eval.py metrics` add the path signals to the result \"merged + oracle green\". For every copy: was there a `Review:` after the last edit, the number of rounds and `Important`, did the `LIVE` command match the Live Scenario, the number of `spec-analyze` findings."
