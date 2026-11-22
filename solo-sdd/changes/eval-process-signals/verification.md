## Live Scenario

The committed fixtures hold only journals in the form Claude Code writes them: `tests/eval/fixtures/signals/` has, for two copies, the dispatcher session journal, the orchestrator and subagent journals with their `.meta.json` files, and the copy's archived `verification.md`. `honest`: one `Lookup:`, `Analyze:`, `Attack:`, `Judge:` and `Check:` agent each, a code edit, `Review: a` with one `Important`, a code edit, `Review: b` with none, a `tasks.md` edit, an `Analyze: 6 findings` line, a `LIVE` command of its Live Scenario. `guess`: a code edit, a `Review:` with an `Important`, a code edit after it, a `LIVE` command outside the Live Scenario, no `Analyze:` line. `tests/stands/eval-process-signals.py` builds the copies as git projects with their oracle commits and the four run logs `r1` to `r4` in a temporary folder (as the `compare` tests build them), lays the journals into a temporary HOME under `.claude/projects/` and runs the real `global/sdd_eval.py` there.

1. The stand runs `sdd_eval.py metrics <tmp> --label r1` → exit 0; `runs/r1.metrics.json` holds for `honest` `review_after_last_edit: true`, `review_rounds: 2`, `important: 1`, `live_in_scenario: true`, `analyze_findings: 6`, and for `guess` `review_after_last_edit: false`, `live_in_scenario: false`, `analyze_findings: null`; the role count of `honest` holds `lookup: 1`, `analyze: 1`, `attack: 1`, `judge: 1`, `check: 1`.
2. The stand runs `sdd_eval.py compare <tmp> --a r1 r2 --b r3 r4` → the report table shows `done` for `honest` and `done, path incomplete` for `guess`, `Done per run` counts both, and `Path:` lists both changes per run.
3. The stand removes the `honest` orchestrator journal and runs `metrics` (exit 0) and `compare` again → `honest` has `null` signals and `done, path unknown`.
4. The stand prints `eval-process-signals: 3 of 3 checks passed`; nothing is written into the tracked tree. The stand call: `python3 tests/stands/eval-process-signals.py`

## Needs

none

## Fallback

Not needed: the fixtures are local, no replay run and no model call.

## Result

2026-11-22: `python3 tests/stands/eval-process-signals.py` printed `eval-process-signals: 3 of 3 checks passed` (metrics r1 signals of honest and guess and the role count; compare marks `done` / `done, path incomplete`, both counted, `Path:` listed; without the honest orchestrator journal: null signals, `done, path unknown`, metrics exit 0). `python3 tests/run.py --jobs 5 --tier slow`: 41 files, 0 failed; `SOLO_SDD_TESTS=release python3 tests/test_sdd_eval.py`: OK; lint and `solo-sdd validate --all` clean.

## Not Verified

- Independent acceptance did not pass: 5 rounds and the extra round, every round after the first left an `Important` in the `important` reader (counting `Important` findings in a reviewer's free text). After the extra round: Russian "net" (none) read as a finding (6 real results 1 instead of 0); Nits: an empty Important section or a status paragraph counted as one finding, a status word at the text start without the clause-end check, a status after a bold colon missed. The commit after the extra round (`29018f6`) fixes these, but no reviewer saw it.
- Reconsider the approach: a heuristic over free text keeps missing forms (measured 143 of 193 exact, 163 of 193 zero-or-not on this computer's journals, 2026-11-22). A fixed verdict line that every `Review:` agent writes (for example `Important: <n>`), set in `skills/spec-next/acceptance.md` and read by `sdd-eval.py`, would make `important` exact; that is a spec-next change outside this one.

## Decisions Without Owner

<!-- Filled during apply: choices made without asking, and new changes created for out-of-scope work. -->

- analyze: order against `goal-first` and `practitioner-techniques`, which also edit `tests/affected.json` → `practitioner-techniques` in Depends On; the plan's chain is linear from here.
- analyze: the judge kept `review_after_last_edit` against the archive gate's first-edit rule (HIGH) → a code edit after the last counted review counts only when that review found an `Important`: spec-next allows Nit fixes without a new round, so an honest path stays `true`.
- analyze: the `live_in_scenario` source and its `null` (HIGH) → the copy's own archived `verification.md` (the `WORKTREE` of a run is temporary and its `ARCHIVE` field is model text), and a missing field, file or section is `null`.
- analyze: the `Analyze:` source (HIGH) → the last `Analyze: <n> findings` line in any orchestrator text; under the dispatcher the report is not printed, so it is often `null`, and the role count (`analyze`, `attack`, `judge`) shows whether the outside run happened.
- analyze: the code-edit rule (MEDIUM) → the gate's `transcript_events` copied as a synced block; paths are judged against the status `WORKTREE` and the copy, since the gate's `git_root` cannot see a removed worktree.
- analyze repeat: hostile journal input (HIGH) → one test row with a broken line and a non-object `.meta.json`; the readers already skip broken lines, a wider fuzz task is out of proportion for the owner's own logs.
- analyze repeat: a reviewer error result (MEDIUM) → only an empty final message is a failed review: an error ends the subagent without a handback or text, so it is empty too.
- review: the `important` reader was measured on the real `Review:` results of this computer's journals each round, besides the reviewer's probes; the README states the figure with its date and status.
- review round 1, I3 (`parentAgentId` in nested `.meta.json`, not verified by the reviewer) → closed without a code edit: this session's own `agent-aa03d6174ed08492f.meta.json` holds `"parentAgentId":"adaec169971171f0a"`.
- review round 5: `jlines` split JSONL with `str.splitlines`, which cuts a record at a raw U+2028 or U+0085 inside a JSON string → split at `\n` only, with a test row; it also makes token counting of such lines complete.
- review round 4, Nit "a label without a separator" (`- Important x`) → left: rare in real results.
