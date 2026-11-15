## Live Scenario

1. `python3 tests/stands/run-decisions.py`: it lays the repository out with `python3 sync.py push` into a temporary home and reads the laid-out `~/.claude/skills/spec-dispatch/SKILL.md`; it prints one `ok` or `FAIL` line per rule and `run-decisions: <n> of <n> checks passed`:
   - the step that handles owner answers writes the line before the recalculation, with the key, under the run's heading;
   - the file choice: `docs/waiting.md` when `git ls-files` does not name it, else `solo-sdd/run-decisions.md` of the git common folder;
   - the heading appended at the start of the run, the file created from its template when missing;
   - the reread of the last section after a summary before the recalculation, earlier sections not read;
   - the report form has the run decisions line.
2. A real dispatcher run in a scratch copy of `examples/demo` with two ready changes that share a file in `Impact`: the owner's answer "Treat <path> as shared until the end of the run", then `/compact`, then the next event → the section in `docs/waiting.md` of the copy holds the `--shared <path>` line, the next plan call passes it and the held change is launched.
3. All tests from the `## Commands` table of `AGENTS.md` → code 0.

## Needs

- Step 2 is one Claude Code dispatcher session with two orchestrators on the scratch demo: it uses the owner's Claude subscription, so it needs the owner's consent before the run.

## Fallback

Without consent: steps 1 and 3 only; Not Verified names step 2, and the next real dispatcher run of the owner is the check.

## Result

<!-- Filled during apply: date, what was run, what was observed. -->

## Not Verified

<!-- Filled during apply: what stayed unproven and why. Write: nothing - if all proven. -->

## Decisions Without Owner

- analyze: after a summary the dispatcher could not know its run's start time to find its section → the heading is appended at the start of the run and the last section is the run's own — the summary may drop the time.
- analyze: no `docs/waiting.md` in the main folder → created from the template — the first answer of a run must not fail on a missing file.
- analyze: a tracked `docs/waiting.md` would make the main folder unclean and stop `land-local` with code 2 → the git common folder file — the merge checks only tracked files.
