## Live Scenario

After `python3 sync.py push`, from the solo-sdd root, on the cheapest model (`cheap` in `global/model-policy.json`):

1. `S="$(mktemp -d)/stand"; cp -R tests/stands/lesson-stand "$S"; cd "$S"; mv AGENTS.long.md AGENTS.md; git init -q; git add -A; git commit -qm stand; sh check.sh`: `## Lessons: 20 lines`, `over 300: 1`, `missing ids: none`, `lost: 0`.
2. `claude -p --model haiku "Make test_get_user pass." < /dev/null`, then `python3 -m unittest -v` (`test_get_user ... ok`) and `sh check.sh`: at most 20 lines, one about awaiting async calls, `over 300: 0`, `missing ids: none`, `lost: 0` (every line of the committed section is either still in the section or verbatim in `LESSONS.md`).
3. `grep -c 'retries a paid call' LESSONS.md` (a phrase only the glued line held): `1`, so its old text was kept, not dropped.
4. A reviewer with a clean context reads the new section and the diff: each line is one rule about a cause, none is two rules joined by a semicolon.
5. `python3 tests/stands/lesson-routing.py` (no models): every check `ok`.

## Needs

- One paid call of `claude -p --model haiku` for step 2 (well under $0.10), on the owner's approval.

## Fallback

Without the paid call: step 1 and step 5 run without models; steps 2-4 are recorded in `Not Verified` with the command to run.

## Result

<!-- Filled during apply: date, what was run, what was observed. -->

## Not Verified

<!-- Filled during apply: what stayed unproven and why. Write: nothing - if all proven. -->

## Decisions Without Owner

- analyze: who reads the full text in `LESSONS.md` → the agent that refines or merges a linked line (the requirement says a refinement edits both) and the owner looking for a cause — a file nobody reads would be a value without a consumer.
- analyze: the live scenario checked only the glued line's text → `check.sh` also prints `lost: <n>` against the committed section, so both merged lines are proven kept — the `Merge names the shared cause` scenario needs it.
- analyze: no property-based test for "no line over the bound after any edit" → the invariant is held by the agent's text, not by code; the stand checks it on real model output and `lesson-routing.py` proves the counting on fixtures — a generator over agent behaviour cannot run without paid calls.
- plan: the bound is 300 characters, fixed in the spec, not a setting → no project asked for another value; the four longest lines of this repository (378-505) are the ones it shortens.
