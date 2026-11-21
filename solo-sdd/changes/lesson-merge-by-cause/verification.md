## Live Scenario

After `python3 sync.py push`, from the solo-sdd root, on the cheapest model (`cheap` in `global/model-policy.json`):

1. `S="$(mktemp -d)/stand"; cp -R tests/stands/lesson-stand "$S"; cd "$S"; mv AGENTS.long.md AGENTS.md; git init -q; git add -A; git commit -qm stand; sh check.sh`: `## Lessons: 20 lines`, `over 300: 1`, `missing ids: none`, `lost: 0`.
2. A subagent of the agent's own Claude Code session on `haiku`, working only in `$S`, gets the prompt "Make test_get_user pass." (never a separate `claude -p` process: lesson `stand-runs-what-it-tests`); then `python3 -m unittest -v` (`test_get_user ... ok`) and `sh check.sh`: at most 20 lines, one about awaiting async calls, `over 300: 0`, `missing ids: none`, `lost: 0` (every line of the committed section is either still in the section or verbatim in `LESSONS.md`).
3. `grep -c 'retries a paid call' LESSONS.md` (a phrase only the glued line held): `1`, so its old text was kept, not dropped.
4. A reviewer with a clean context reads the new section and the diff: each line is one rule about a cause, none is two rules joined by a semicolon.
5. `python3 tests/stands/lesson-routing.py` (no models): every check `ok`.

## Needs

- One `haiku` subagent run of the session for step 2 (well under $0.10), launched by a session whose hook allows such a subagent (the main session, not an orchestrator under `spec-dispatch`, which may launch only `Review:` and `Lookup:`).

## Fallback

Without that subagent run: step 1 and step 5 run without models (step 5 covers step 1 on the same fixture), step 4 is done by the change's `Review:` reviewer; steps 2-3 are recorded in `Not Verified` with the prompt to run.

## Result

<!-- Filled during apply: date, what was run, what was observed. -->

## Not Verified

<!-- Filled during apply: what stayed unproven and why. Write: nothing - if all proven. -->

## Decisions Without Owner

- analyze: who reads the full text in `LESSONS.md` → the agent that refines or merges a linked line (the requirement says a refinement edits both) and the owner looking for a cause — a file nobody reads would be a value without a consumer.
- analyze: the live scenario checked only the glued line's text → `check.sh` also prints `lost: <n>` against the committed section, so both merged lines are proven kept — the `Merge names the shared cause` scenario needs it.
- analyze: no property-based test for "no line over the bound after any edit" → the invariant is held by the agent's text, not by code; the stand checks it on real model output and `lesson-routing.py` proves the counting on fixtures — a generator over agent behaviour cannot run without paid calls.
- plan: the bound is 300 characters, fixed in the spec, not a setting → no project asked for another value; the four longest lines of this repository (378-505) are the ones it shortens.
- analyze: step 2 ran the model through `claude -p`, which the repository lesson `stand-runs-what-it-tests` forbids → the step runs a `haiku` subagent of the agent's own session; an orchestrator under the dispatcher cannot launch it, so the Fallback names that case — the owner allows a model run only in that form.
- analyze: what `check.sh` measures was open → a line's length is its characters after `- ` and before the optional ` ([full text](LESSONS.md#<id>))` link; `lost` looks for that text with whitespace collapsed in the current section's texts and in `LESSONS.md` — the bound in the requirement is "before an optional link", and the lesson `output-checks-by-prefix` matches whole items with whitespace collapsed.
- analyze: task 1.3 keeps the full text unchanged while the requirement keeps a shortened line's old text verbatim → each of the four sections keeps its full text and gets the old line appended verbatim as its last paragraph — both hold, and `lost: 0` holds for this repository too.
