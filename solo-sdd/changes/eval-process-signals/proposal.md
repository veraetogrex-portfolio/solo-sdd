# Proposal

## Why

`sdd-eval.py` counts a change as done when it is merged and the oracle tests pass on the result. A run that guessed right without an honest path (no review after the last code edit, a `LIVE` command that is not the Live Scenario's, no `spec-analyze` pass) scores the same as one that followed the process, so a configuration that skips steps can look as good as one that keeps them. The signals of the path are already in the data the metrics read: the session journals of the dispatcher and its subagents, and the copy's `verification.md`. Counting them needs no paid run.

## What Changes

- `sdd-eval.py metrics` adds, for every copy, the signals of the path read from the journal of the orchestrator that handed back `archived`: whether a `Review:` agent came after the last code edit (Nit fixes after a review without an `Important` allowed, as spec-next allows them), the number of counted review rounds and of `Important` findings in their results, whether the `LIVE` command of the status is a code span of the Live Scenario of the copy's archived `verification.md` (by the reader `sdd-dispatch.py accept` uses, never run), and `<n>` of the orchestrator's last `Analyze: <n> findings` line, `null` when the line is missing.
- The journal events are read by the archive gate's own reader: `transcript_events` of `global/work_hooks.py` becomes a block that `scripts/sync_blocks.py` copies into `global/sdd_eval.py`.
- The subagent count by role adds `lookup`, `analyze`, `attack`, `judge` and `check`.
- `sdd-eval.py compare` shows the signals per change and run next to `done`, and marks `done, path incomplete` a change that is done but has no review after the last edit or a `LIVE` outside the Live Scenario, and `done, path unknown` one whose signals could not be read.
- Every `Review:` agent ends its answer with the line `Important: <n>` (`skills/spec-next/acceptance.md`); `important` reads that line and falls back to the labelled lines of an older review without it, and `metrics` names the source of each count in `important_sources`.
- `tests/eval/README.md` describes the signals and how each is read.

## Capabilities

### New Capabilities

### Modified Capabilities
- `spec-next`: ADDED requirement Review verdict line; MODIFIED requirement Reviewer failure.
- `dispatch-eval`: ADDED requirements Process path signals, What the review signals read, Review verdict count, What the status and analyze signals read, Path marks in the comparison; MODIFIED requirements Metrics by one method, Oracle tests and comparison.

## Impact

- `global/sdd_eval.py`
- `skills/spec-next/acceptance.md`
- `tests/test_skill_commands.py`
- `global/work_hooks.py`
- `scripts/sync_blocks.py`
- `tests/test_sdd_eval.py`
- `tests/eval/fixtures/`
- `tests/affected.json`
- `tests/stands/eval-process-signals.py`
- `tests/eval/README.md`

## Out of Scope

- A replay run of the set and the eval baseline: they need 4-7 h and about $80-200 per run and wait in `docs/waiting.md` (`dispatch-eval-replay`).
- Changing the "done" rule (merged and oracle green): the signals stand next to it.
- Neighbouring changes of this plan: `subagent-check-roles`, `analyze-outside`, `outside-check-text`, `source-over-paste`, `goal-first`, `practitioner-techniques`, `skill-ablation`, `work-pull`, `review-principles` (it also edits `skills/spec-next/acceptance.md`, another line: the `REVIEW.md` hand-over).

## Depends On

- subagent-check-roles
- analyze-outside
- practitioner-techniques

## Source

The owner, 2026-11-20 (translated from Russian): "A separate small unit `eval-process-signals`: in `sdd-eval.py metrics` add the path signals to the result \"merged + oracle green\". For every copy: was there a `Review:` after the last edit, the number of rounds and `Important`, did the `LIVE` command match the Live Scenario, the number of `spec-analyze` findings."

The owner, 2026-11-22, relayed by the dispatcher (its words): "The owner chose your second option, inside this change: every `Review:` agent writes a fixed verdict line `Important: <n>` (the rule goes into skills/spec-next/acceptance.md, where the reviewer prompt is built), and sdd-eval.py's `important` reads that line; for journals without the line (older reviews) keep the current heuristic as the fallback and report which source each count came from."
